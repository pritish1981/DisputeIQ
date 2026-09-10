import { useState, type FormEvent } from "react";
import { listControlEvaluations, type ControlEvaluation } from "./controls";

export function ControlViewer() {
  const [workflowId, setWorkflowId] = useState("");
  const [items, setItems] = useState<ControlEvaluation[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function lookup(event: FormEvent) {
    event.preventDefault(); setError(""); setItems([]); setLoading(true);
    try { setItems((await listControlEvaluations(workflowId.trim())).items); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "Lookup failed."); }
    finally { setLoading(false); }
  }
  return <section className="panel controls">
    <h2>Deterministic controls</h2>
    <p>Evidence, policy applicability, rule findings and governed confidence. Results support
      a recommendation; material financial outcomes require human review.</p>
    <form onSubmit={lookup}>
      <label>Workflow ID<input required value={workflowId}
        onChange={event => setWorkflowId(event.target.value)} /></label>
      <button disabled={loading}>{loading ? "Loading evaluations..." : "Load evaluations"}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {!loading && items.length === 0 && <p>No evaluations loaded.</p>}
    {items.map(item => <ControlDetail key={item.evaluation_id} item={item} />)}
  </section>;
}

export function ControlDetail({ item }: { item: ControlEvaluation }) {
  const { evidence, policy, rules, confidence } = item.stages;
  return <article className="detail">
    <h3>Evaluation {item.evaluation_id}</h3>
    <p>{item.bundle.evaluated_at} · Profile {item.bundle.profile_version ?? "unavailable"}</p>
    {item.bundle.prior_evaluation_id && <p>Re-evaluates {item.bundle.prior_evaluation_id}</p>}
    <h4>Pinned versions</h4>
    <dl>{Object.entries(item.bundle.versions).map(([name, version]) =>
      <div key={name}><dt>{name}</dt><dd>{version}</dd></div>)}</dl>
    <h4>Evidence completeness</h4>
    {evidence ? <>
      <p>Score {evidence.score} · Mandatory gate: {evidence.mandatory_complete ? "passed" : "blocked"}</p>
      <ul>{evidence.required.map(name => <li key={name}>{name}: {
        evidence.satisfaction[name]?.length ? "satisfied" : "unsatisfied"}</li>)}</ul>
      {(["available", "missing", "stale", "invalid", "conflicting"] as const).map(kind =>
        <p key={kind}>{kind}: {evidence[kind].join(", ") || "none"}</p>)}
      <p>{evidence.reasons.join(", ")}</p>
    </> : <p>Not evaluated.</p>}
    <h4>Admitted policy</h4>
    {policy ? <><p>{policy.approved_context ? "Admitted" : "Review required"} ·
      Corpus {policy.corpus_version} · Index {policy.index_version}</p>
      <ul>{policy.citations.map(citation => <li key={citation.chunk_hash}>
        {citation.document_id} · {citation.version} · {citation.section}</li>)}</ul>
      <p>{policy.reasons.join(", ")}</p></> : <p>Not evaluated.</p>}
    <h4>Deterministic rule findings</h4>
    {rules ? <><p>Disposition candidate: <strong>{rules.candidate}</strong></p>
      <div className="control-table"><table><thead><tr><th>Rule / version</th><th>Outcome</th><th>Reason</th></tr></thead>
        <tbody>{rules.results.map(rule => <tr key={rule.rule_id}>
          <td>{rule.rule_id} / {rule.version}</td><td>{rule.outcome}</td><td>{rule.reason_code}</td>
        </tr>)}</tbody></table></div></> : <p>Not evaluated.</p>}
    <h4>Governed confidence</h4>
    <p>AI classification is one input signal. The aggregate below is computed by versioned rules.</p>
    {confidence ? <><p>Score {confidence.score} · Threshold {confidence.threshold} · {
      confidence.ready ? "Ready for recommendation boundary" : "Blocked"}</p>
      <div className="control-table"><table><thead><tr><th>Signal</th><th>Raw</th><th>Normalized</th><th>Weight</th><th>Contribution</th></tr></thead>
        <tbody>{Object.entries(confidence.factors).map(([name, factor]) => <tr key={name}>
          <td title={factor.source_ref}>{name}{factor.valid ? "" : " (unknown)"}</td>
          <td>{factor.raw ?? "unknown"}</td><td>{factor.normalized}</td>
          <td>{factor.weight}</td><td>{factor.contribution}</td>
        </tr>)}</tbody></table></div><p>{confidence.reasons.join(", ")}</p></> : <p>Not evaluated.</p>}
    <h4>Review requests</h4>
    {item.requests.length ? <ul>{item.requests.map(request => <li key={request.request_id}>
      {request.kind} · {request.status} · {request.reasons.join(", ")}</li>)}</ul> : <p>None.</p>}
    <details><summary>Input integrity</summary><p>{item.bundle.inputs_hash}</p>
      <p>Classification snapshot: {item.bundle.classification_hash}</p></details>
  </article>;
}
