## MODIFIED Requirements

### Requirement: Deterministic evidence completeness
FRD reference: FR-EVD-003, FR-ARC-003

The platform SHALL determine required, available, missing, stale and conflicting evidence through controlled deterministic logic.

#### Scenario: Evidence checklist evaluated
- **GIVEN** uploaded evidence and authoritative context exist
- **WHEN** completeness is evaluated
- **THEN** required, available, missing, stale and conflicting evidence are identified
- **AND** mandatory completeness status is produced by controlled deterministic logic

#### Scenario: Phase 002 evidence metadata persists without AI analysis
- **GIVEN** a Phase 002 synthetic duplicate-card case contains evidence metadata
- **WHEN** evidence metadata is registered or returned
- **THEN** the metadata is persisted and retrieved without invoking AI-assisted document analysis
- **AND** any completeness status exposed by Phase 002 is deterministic and marked as preliminary when full workflow evidence gates are not yet enabled

## ADDED Requirements

### Requirement: Evidence metadata registration
FRD reference: FR-EVD-001, FR-EVD-002

The platform SHALL allow authorized callers to register evidence metadata for a case without requiring binary document processing in Phase 002.

#### Scenario: Register evidence metadata
- **GIVEN** an authorized caller submits valid evidence metadata for an existing case
- **WHEN** the metadata command is accepted
- **THEN** an immutable evidence identifier is created
- **AND** metadata including evidence type, file/object reference where provided, checksum, content type, size, source, status, uploader reference, timestamp, and correlation ID is persisted
- **AND** a material evidence timeline and audit record is created

#### Scenario: Reject invalid evidence metadata
- **GIVEN** evidence metadata is missing required fields or contains an invalid checksum or unsupported evidence type
- **WHEN** the caller submits the metadata command
- **THEN** the request is rejected with structured field-level validation errors
- **AND** no evidence metadata record is created

### Requirement: Evidence metadata listing
FRD reference: FR-EVD-001, FR-EVD-002, FR-EVD-003

The platform SHALL allow authorized callers to list evidence metadata associated with a case.

#### Scenario: List case evidence metadata
- **GIVEN** a case has registered evidence metadata
- **WHEN** an authorized caller requests the case evidence metadata
- **THEN** evidence metadata records are returned in deterministic order
- **AND** each record includes status, source, lineage, and correlation fields required for audit reconstruction

#### Scenario: Evidence metadata for unknown case
- **GIVEN** no case exists for the requested case ID
- **WHEN** a caller requests evidence metadata for that case
- **THEN** a structured not-found response is returned
