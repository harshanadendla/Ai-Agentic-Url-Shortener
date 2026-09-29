# Required scenarios

## Greenfield
**Requirement:** add a bulk URL-shortening endpoint limited to 100 URLs while preserving single-link behavior.

Expected behavior: the requirement is decomposed; design agents run in parallel; risk is low, so configured policy may auto-approve; the implementation agent stages a Java `BulkShortenPolicy`, a JUnit test, and OpenAPI fragment; validation completes at the exit gate.

## Brownfield
**Requirement:** extend analytics with daily UTC click buckets using an additive schema migration while preserving current fields.

Expected behavior: the Java codebase is scanned to identify impacted controllers/services/repositories/schema; `schema`/`migration` raises the risk level to medium; human approval is required before implementation; staged output demonstrates backward-compatible evolution.

## Ambiguous
**Requirement:** make analytics “better and fast” for enterprise users without breaking clients.

Expected behavior: the requirements agent identifies “better” and “fast” as ambiguous; the run stops at the human approval gate; the reviewer supplies a measurable SLO (for example p95 <= 200 ms) and compatibility constraint; that clarification is preserved in assumptions/decision lineage before execution resumes.
