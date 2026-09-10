"""Transactional orchestration adapters for the pure Phase 007 services."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.control_context import ControlContextAdapter
from app.adapters.control_repository import ControlConfigurationError, ControlRepository
from app.adapters.models import (
    CaseModel,
    ControlEvaluationModel,
    ControlRequestFulfillmentModel,
    ControlReviewRequestModel,
    EvidenceValidationModel,
    PolicyChunkModel,
    PolicyCorpusVersionModel,
    PolicyDocumentModel,
)
from app.adapters.repositories import AuditRepository
from app.core.config import settings
from app.domain.controls import (
    ControlProfile,
    EvaluationBundle,
    EvidenceAssessment,
    EvidenceItem,
    ReevaluationRequest,
    digest,
)
from app.domain.schemas import PolicyRetrievalRequest
from app.services.case_confidence import ConfidenceService, rule_certainty
from app.services.evidence_completeness import EvidenceCompletenessService
from app.services.policy_eligibility import PolicyEligibilityService, db_utc
from app.services.policy_retrieval import PolicyRetrievalService
from app.services.rules_engine import RulesEngine, instant
from app.services.workflow_graph import WorkflowState


class ControlWorkflow:
    def __init__(
        self,
        db: Session,
        policy: PolicyRetrievalService,
        audit: AuditRepository,
        context: ControlContextAdapter | None = None,
    ) -> None:
        self.db = db
        self.repo = ControlRepository(db)
        self.policy = policy
        self.audit = audit
        self.context = context or ControlContextAdapter()
        self.evaluation: ControlEvaluationModel | None = None
        self.profile: ControlProfile | None = None
        self.at = datetime.now(UTC)

    def nodes(self) -> dict[str, Any]:
        return {
            "authoritative_context": self.prepare,
            "evidence_gate": self.evidence,
            "policy_context": self.resolve_policy,
            "rules": self.rules,
            "confidence": self.confidence,
            "controlled_stop": self.finish,
        }

    def _row(self) -> ControlEvaluationModel:
        if self.evaluation is None:
            raise RuntimeError("Control evaluation not initialized")
        return self.evaluation

    def _profile(self) -> ControlProfile:
        if self.profile is None:
            raise ControlConfigurationError("CONTROL_PROFILE_UNAVAILABLE")
        return self.profile

    def _audit(self, event: str, metadata: dict[str, Any]) -> None:
        row = self._row()
        case = self.db.get(CaseModel, row.case_id)
        if case is None:
            raise LookupError("Case not found")
        self.audit.append(
            case=case,
            event_type=event,
            object_ref=row.evaluation_id,
            state_version=row.state_version,
            correlation_id=row.correlation_id,
            metadata={
                "evaluation_id": row.evaluation_id,
                "workflow_id": row.workflow_id,
                "actor_ref": row.actor_ref,
                "bundle_hash": row.bundle_hash,
                **metadata,
            },
            now=self.at,
        )

    def _record(self, stage: str, result: dict[str, Any], state: WorkflowState) -> None:
        result_id = self.repo.add_stage(self._row(), stage, result, self.at)
        summary: dict[str, object] = {
            "evaluation_id": self._row().evaluation_id,
            "result_id": result_id,
            "result_hash": digest(result),
            **{
                key: result[key]
                for key in ("score", "ready", "candidate", "mandatory_complete")
                if key in result
            },
        }
        state.setdefault("stage_summaries", {})[stage] = summary
        events = {
            "evidence": "EVIDENCE_ASSESSED",
            "policy": "POLICY_ELIGIBILITY_EVALUATED",
            "rules": "RULES_EXECUTED",
            "confidence": "CASE_CONFIDENCE_EVALUATED",
        }
        self._audit(
            events[stage],
            {
                "stage": stage,
                "result_id": result_id,
                "result_hash": digest(result),
                "reasons": result.get("reasons", []),
            },
        )

    def _wait(
        self,
        state: WorkflowState,
        kind: str,
        reasons: list[str],
        required_items: list[str] | None = None,
    ) -> None:
        status, role = {
            "REQUEST_ADDITIONAL_EVIDENCE": ("WAITING_EVIDENCE", "analyst"),
            "POLICY_REVIEW": ("WAITING_POLICY_REVIEW", "policy-reviewer"),
            "MANUAL_REVIEW": ("WAITING_RULE_REVIEW", "analyst"),
            "SUPERVISOR_REVIEW": ("WAITING_SUPERVISOR_REVIEW", "supervisor"),
        }[kind]
        row = self._row()
        request = self.db.scalar(
            select(ControlReviewRequestModel).where(
                ControlReviewRequestModel.evaluation_id == row.evaluation_id,
                ControlReviewRequestModel.kind == kind,
            )
        )
        if request is None:
            request = ControlReviewRequestModel(
                request_id=str(uuid4()),
                evaluation_id=row.evaluation_id,
                kind=kind,
                required_role=role,
                reasons=sorted(set(reasons)),
                required_items=required_items or [],
                correlation_id=row.correlation_id,
                created_at=self.at,
            )
            self.db.add(request)
            self.db.flush()
            self._audit(
                "CONTROL_REVIEW_REQUESTED",
                {"request_id": request.request_id, "kind": kind, "reasons": reasons},
            )
        state["status"] = status
        state["interrupt"] = {
            "required": True,
            "reason": reasons[0] if reasons else kind,
            "message": f"{kind} required; no automatic approval is available.",
            "resume_requirements": ["changed_validated_inputs", "authorized_reevaluation"],
        }

    def prepare(self, state: WorkflowState) -> WorkflowState:
        case = dict(cast(dict[str, Any], state["case"]))
        if self.db.get_bind().dialect.name == "sqlite":
            # SQLite drops timezone on persisted UTC datetimes; restore only at this DB boundary.
            submitted = datetime.fromisoformat(str(case["submitted_at"]).replace("Z", "+00:00"))
            if submitted.tzinfo is None:
                case["submitted_at"] = submitted.replace(tzinfo=UTC).isoformat()
        facts, items = self.context.acquire(case)
        self.at = datetime.now(UTC)
        for evidence in case.get("evidence_metadata", []):
            validation = self.db.get(EvidenceValidationModel, evidence["evidence_id"])
            valid = (
                validation is not None
                and validation.status == "validated"
                and (validation.checksum == evidence["checksum_sha256"])
            )
            items.append(
                EvidenceItem(
                    reference=evidence["evidence_id"],
                    kind=evidence["evidence_type"],
                    checksum=evidence["checksum_sha256"],
                    state="validated" if valid else "unknown",
                    attributes={
                        "validation_ref": validation.provenance if validation else "unknown"
                    },
                )
            )
        classification = state.get("stage_summaries", {}).get("classification", {})
        config_id = None
        errors = []
        prior: ControlEvaluationModel | None = None
        reevaluation: ReevaluationRequest | None = None
        if state.get("resume_payload", {}).get("reevaluation"):
            reevaluation = ReevaluationRequest.model_validate(
                state["resume_payload"]["reevaluation"]
            )
            prior = self.repo.get(state["workflow_id"], reevaluation.prior_evaluation_id)
        try:
            if prior and reevaluation and reevaluation.retain_pins:
                if not prior.config_id:
                    raise ControlConfigurationError("PINNED_CONFIGURATION_UNAVAILABLE")
                config_id = prior.config_id
                self.profile = self.repo.profile(config_id)
            else:
                config_id, self.profile = self.repo.resolve(
                    environment=settings.app_env,
                    dispute_type=case["dispute_type"],
                    product=facts["account"].get("product", ""),
                    channel=case["channel"],
                    jurisdiction=facts["merchant"].get("country", ""),
                    at=self.at,
                )
        except ControlConfigurationError as exc:
            errors.append(str(exc))
        except ValueError:
            errors.append("INVALID_CONTROL_CONFIGURATION")
        profile = self.profile
        if profile and (
            profile.dispute_type != case["dispute_type"]
            or profile.product != facts["account"].get("product")
            or case["channel"] not in profile.channels
            or facts["merchant"].get("country") not in profile.jurisdictions
        ):
            errors.append("PINNED_PROFILE_SCOPE_MISMATCH")
        versions = (
            {}
            if profile is None
            else {
                "evidence_contract": profile.evidence.version,
                "eligibility": profile.eligibility.version,
                "ruleset": profile.rules.version,
                "confidence": profile.confidence.version,
            }
        )
        inputs = {
            "facts": facts,
            "evidence": [item.model_dump(mode="json") for item in items],
            "classification": classification,
            "channel": case["channel"],
        }
        # Provider retrieval timestamps are not semantic input; source-as-of is retained.
        for record in facts["provider_records"]:
            record.pop("retrieved_at", None)
        bundle = EvaluationBundle(
            case_id=state["case_id"],
            workflow_id=state["workflow_id"],
            state_version=state["state_version"],
            evaluated_at=self.at,
            profile_id=profile.profile_id if profile else None,
            profile_version=profile.version if profile else None,
            profile_hash=digest(profile) if profile else None,
            inputs_hash=digest(inputs),
            classification_hash=digest(classification),
            evidence_hash=digest(items),
            facts_hash=digest(facts),
            versions=versions,
            prior_evaluation_id=prior.evaluation_id if prior else None,
            reevaluation_reason=reevaluation.reason if reevaluation else None,
        )
        self.evaluation = ControlEvaluationModel(
            evaluation_id=str(uuid4()),
            workflow_id=state["workflow_id"],
            case_id=state["case_id"],
            state_version=state["state_version"],
            config_id=config_id,
            prior_evaluation_id=bundle.prior_evaluation_id,
            bundle=bundle.model_dump(mode="json"),
            inputs=inputs,
            bundle_hash=digest(bundle),
            correlation_id=state["correlation_id"],
            actor_ref=str(state.get("resume_payload", {}).get("actor_ref", "workflow-service")),
            created_at=self.at,
        )
        self.db.add(self.evaluation)
        self.db.flush()
        state["control_evaluation_id"] = self.evaluation.evaluation_id
        self._audit(
            "CONTROL_CONTEXT_CAPTURED",
            {
                "facts_hash": bundle.facts_hash,
                "inputs_hash": bundle.inputs_hash,
                "profile_hash": bundle.profile_hash,
            },
        )
        state.setdefault("stage_summaries", {})["authoritative_context"] = {
            "evaluation_id": self.evaluation.evaluation_id,
            "facts_hash": bundle.facts_hash,
            "reference_count": len(facts["references"]),
            "versions": versions,
        }
        if prior:
            self._audit(
                "CONTROL_REEVALUATED",
                {"prior_evaluation_id": prior.evaluation_id, "reason": bundle.reevaluation_reason},
            )
        if errors:
            self._wait(state, "MANUAL_REVIEW", errors)
        elif facts["provider_errors"]:
            self._wait(state, "MANUAL_REVIEW", facts["provider_errors"])
        return state

    def evidence(self, state: WorkflowState) -> WorkflowState:
        row = self._row()
        result = EvidenceCompletenessService().assess(
            self._profile().evidence,
            [EvidenceItem.model_validate(i) for i in cast(list[Any], row.inputs["evidence"])],
            self.at,
        )
        self._record("evidence", result.model_dump(mode="json"), state)
        if not result.mandatory_complete:
            self._wait(
                state,
                "MANUAL_REVIEW" if result.conflicting else "REQUEST_ADDITIONAL_EVIDENCE",
                result.reasons or ["MANDATORY_EVIDENCE_INCOMPLETE"],
                [
                    r.requirement_id
                    for r in self._profile().evidence.requirements
                    if r.mandatory and not result.satisfaction[r.requirement_id]
                ],
            )
        elif row.prior_evaluation_id:
            for request in self.db.scalars(
                select(ControlReviewRequestModel).where(
                    ControlReviewRequestModel.evaluation_id == row.prior_evaluation_id,
                    ControlReviewRequestModel.kind == "REQUEST_ADDITIONAL_EVIDENCE",
                )
            ):
                if self.db.get(ControlRequestFulfillmentModel, request.request_id) is None:
                    self.db.add(
                        ControlRequestFulfillmentModel(
                            request_id=request.request_id,
                            evaluation_id=row.evaluation_id,
                            created_at=self.at,
                        )
                    )
                    self._audit("CONTROL_REQUEST_FULFILLED", {"request_id": request.request_id})
        return state

    def _policy_source_hash(self, chunk: PolicyChunkModel) -> str:
        return digest(
            {
                "content": chunk.content,
                "chunk_hash": chunk.chunk_hash,
                "source_checksum": chunk.source_checksum_sha256,
                "product": chunk.product,
                "channel": chunk.channel,
                "jurisdiction": chunk.jurisdiction,
                "effective_from": db_utc(chunk.effective_from),
                "effective_to": db_utc(chunk.effective_to) if chunk.effective_to else None,
            }
        )

    def _validate_policy(self, result: dict[str, Any]) -> list[str]:
        allowed = {(p.document_id, p.version) for p in self._profile().eligibility.mappings}
        reasons = []
        facts = cast(dict[str, Any], self._row().inputs["facts"])
        effective = instant(facts["disputed"]["authorized_at"])
        for citation in result.get("citations", []):
            chunk = self.db.scalar(
                select(PolicyChunkModel).where(PolicyChunkModel.chunk_id == citation["chunk_id"])
            )
            document = self.db.get(PolicyDocumentModel, chunk.policy_document_pk) if chunk else None
            content_hash = (
                hashlib.sha256(
                    "|".join(
                        [
                            chunk.document_id,
                            chunk.version,
                            chunk.section,
                            chunk.source_checksum_sha256,
                            chunk.parser_version,
                            chunk.chunking_config_hash,
                            chunk.content,
                        ]
                    ).encode()
                ).hexdigest()
                if chunk
                else None
            )
            if (
                not chunk
                or not document
                or chunk.chunk_hash != citation["chunk_hash"]
                or content_hash != chunk.chunk_hash
                or document.source_checksum_sha256 != chunk.source_checksum_sha256
                or document.product != chunk.product
                or document.channel != chunk.channel
                or document.jurisdiction != chunk.jurisdiction
                or self._policy_source_hash(chunk)
                != result.get("source_hashes", {}).get(chunk.chunk_id)
                or chunk.product != facts["account"]["product"]
                or chunk.channel != self._row().inputs["channel"]
                or chunk.jurisdiction != facts["merchant"]["country"]
                or db_utc(chunk.effective_from) > effective
                or (chunk.effective_to is not None and db_utc(chunk.effective_to) < effective)
                or db_utc(document.effective_from) > effective
                or (document.effective_to is not None and db_utc(document.effective_to) < effective)
                or (
                    document.status not in {"approved", "active"}
                    or chunk.status not in {"approved", "active"}
                    or not document.approval_ref
                    or (citation["document_id"], citation["version"]) not in allowed
                    or chunk.document_id != citation["document_id"]
                    or chunk.version != citation["version"]
                )
            ):
                reasons.append("PINNED_POLICY_UNAVAILABLE_OR_REVOKED")
        if not result.get("citations"):
            reasons.append("MISSING_CITED_POLICY")
        return reasons

    def resolve_policy(self, state: WorkflowState) -> WorkflowState:
        row = self._row()
        facts = cast(dict[str, Any], row.inputs["facts"])
        prior_result = (
            self.repo.stage(row.prior_evaluation_id, "policy")
            if (row.prior_evaluation_id)
            else None
        )
        reevaluation = state.get("resume_payload", {}).get("reevaluation", {})
        retain = isinstance(reevaluation, dict) and reevaluation.get("retain_pins", True)
        if prior_result and prior_result.get("approved_context") and retain:
            result = dict(prior_result)
            reasons = self._validate_policy(result)
            corpus = self.db.scalar(
                select(PolicyCorpusVersionModel).where(
                    PolicyCorpusVersionModel.corpus_version == result.get("corpus_version")
                )
            )
            if corpus:
                effective = instant(facts["disputed"]["authorized_at"])
                result["eligibility"] = PolicyEligibilityService().evaluate(
                    self.policy.repository,
                    corpus,
                    PolicyRetrievalRequest(
                        query="pinned policy applicability",
                        effective_date=effective,
                        product=facts["account"]["product"],
                        channel=str(row.inputs["channel"]),
                        jurisdiction=facts["merchant"]["country"],
                        actor_ref=row.actor_ref,
                    ),
                    self._profile().eligibility,
                )
                result["effective_as_of"] = effective.isoformat()
                if not {c["chunk_id"] for c in result["citations"]} <= set(
                    result["eligibility"]["eligible_chunk_ids"]
                ):
                    reasons.append("PINNED_POLICY_NO_LONGER_APPLICABLE")
            else:
                reasons.append("PINNED_CORPUS_UNAVAILABLE")
        else:
            try:
                effective = instant(facts["disputed"]["authorized_at"])
                request = PolicyRetrievalRequest(
                    query="duplicate card transaction issuer review evidence merchant context",
                    effective_date=effective,
                    product=facts["account"]["product"],
                    channel=str(row.inputs["channel"]),
                    jurisdiction=facts["merchant"]["country"],
                    case_id=UUID(row.case_id),
                    workflow_id=UUID(row.workflow_id),
                    actor_ref=row.actor_ref,
                )
                response = self.policy.retrieve(
                    request,
                    correlation_id=row.correlation_id,
                    eligibility_profile=self._profile().eligibility,
                )
                result = {
                    "approved_context": response.approved_context,
                    "confidence": response.confidence,
                    "eligibility": response.eligibility,
                    "corpus_version": response.corpus_version,
                    "index_version": response.index_version,
                    "retrieval_config": response.retrieval_config.model_dump(mode="json"),
                    "effective_as_of": effective.isoformat(),
                    "citations": [r.citation.model_dump(mode="json") for r in response.results],
                    "source_hashes": {
                        chunk.chunk_id: self._policy_source_hash(chunk)
                        for r in response.results
                        if (
                            chunk := self.db.scalar(
                                select(PolicyChunkModel).where(
                                    PolicyChunkModel.chunk_id == r.citation.chunk_id
                                )
                            )
                        )
                        is not None
                    },
                }
                reasons = [response.abstention_reason.value] if response.abstention_reason else []
                reasons += self._validate_policy(result)
            except (KeyError, ValueError, TimeoutError, ConnectionError):
                result = {"approved_context": False, "citations": [], "confidence": None}
                reasons = ["POLICY_RESOLUTION_UNAVAILABLE"]
        result["reasons"] = sorted(set(reasons))
        result["approved_context"] = bool(result.get("approved_context")) and not reasons
        self._record("policy", result, state)
        if not result["approved_context"]:
            self._wait(state, "POLICY_REVIEW", reasons or ["POLICY_REVIEW_REQUIRED"])
        return state

    def rules(self, state: WorkflowState) -> WorkflowState:
        row = self._row()
        policy = self.repo.stage(row.evaluation_id, "policy") or {}
        evidence = EvidenceAssessment.model_validate(self.repo.stage(row.evaluation_id, "evidence"))
        result = RulesEngine().execute(
            self._profile().rules,
            cast(dict[str, Any], row.inputs["facts"]),
            evidence,
            [f"{c['document_id']}:{c['version']}" for c in policy.get("citations", [])],
            self.at,
        )
        self._record("rules", result.model_dump(mode="json"), state)
        if result.blocked:
            self._wait(
                state,
                "MANUAL_REVIEW",
                [r.reason_code for r in result.results if r.outcome in {"ERROR", "INDETERMINATE"}],
            )
        return state

    def confidence(self, state: WorkflowState) -> WorkflowState:
        from app.domain.controls import RuleExecution

        row = self._row()
        facts = cast(dict[str, Any], row.inputs["facts"])
        classification = cast(dict[str, Any], row.inputs["classification"])
        evidence = EvidenceAssessment.model_validate(self.repo.stage(row.evaluation_id, "evidence"))
        policy = self.repo.stage(row.evaluation_id, "policy") or {}
        rules = RuleExecution.model_validate(self.repo.stage(row.evaluation_id, "rules"))
        gates = []
        for passed, reason in (
            (classification.get("accepted"), "CLASSIFICATION_NOT_ACCEPTED"),
            (evidence.mandatory_complete, "MANDATORY_EVIDENCE_INCOMPLETE"),
            (policy.get("approved_context"), "POLICY_NOT_ADMITTED"),
            (not rules.blocked, "RULE_REVIEW_REQUIRED"),
            (not evidence.conflicting, "CONTEXT_CONFLICT"),
            (not facts["provider_errors"], "REQUIRED_PROVIDER_FAILURE"),
        ):
            if not passed:
                gates.append(reason)
        signals = {
            "classification": classification.get("confidence"),
            "evidence": evidence.score,
            "policy": policy.get("confidence"),
            "rules": rule_certainty(rules),
            "conflicts": int(bool(evidence.conflicting)),
            "tools": Decimal(len(facts["provider_errors"])) / facts["required_operations"],
        }
        summaries = cast(dict[str, dict[str, Any]], state.get("stage_summaries", {}))
        refs = {
            key: str(summaries.get(key, {}).get("result_id", f"{row.evaluation_id}:{key}"))
            for key in signals
        }
        refs["classification"] = f"{row.evaluation_id}:classification:{digest(classification)}"
        refs["conflicts"] = refs["evidence"]
        refs["tools"] = f"{row.evaluation_id}:facts:{digest(facts)}"
        result = ConfidenceService().evaluate(self._profile().confidence, signals, refs, gates)
        result = result.model_copy(
            update={
                "pins": {
                    "bundle_hash": row.bundle_hash,
                    "profile_hash": digest(self._profile()),
                    "evidence_contract": self._profile().evidence.version,
                    "evidence_result": summaries["evidence"],
                    "policy_result": summaries["policy"],
                    "rule_result": summaries["rules"],
                    "policy_corpus": policy.get("corpus_version"),
                    "policy_index": policy.get("index_version"),
                    "policy_citations": policy.get("citations", []),
                    "retrieval_config": policy.get("retrieval_config"),
                    "ruleset": self._profile().rules.version,
                    "disposition": self._profile().rules.disposition_version,
                    "confidence_config": self._profile().confidence.model_dump(mode="json"),
                }
            }
        )
        self._record("confidence", result.model_dump(mode="json"), state)
        if not result.ready:
            self._wait(state, "SUPERVISOR_REVIEW", result.reasons)
        return state

    def finish(self, state: WorkflowState) -> WorkflowState:
        state["status"] = "CONTROLLED_STOP"
        state["interrupt"] = {
            "required": True,
            "reason": "deterministic_disposition_ready",
            "message": "Deterministic evaluation ready for recommendation and human review.",
            "resume_requirements": ["phase_008_recommendation_and_human_decision"],
        }
        state.setdefault("stage_summaries", {})["controlled_stop"] = {
            "evaluation_id": self._row().evaluation_id,
            "next_boundary": "recommendation_and_human_decision",
            "financial_outcome_finalized": False,
            "communication_sent": False,
        }
        return state
