# GSoC Proposal Draft: openPIP 2.0

## About

1. Full Name: Aryan Mishra
2. Public Email: aryanmi2001@gmail.com
3. Discord Handle: alaotach
4. GitHub Profile: https://github.com/alaotach
5. Time Zone: [UTC+05:30]
6. University: Jawaharlal Nehru University
7. Program and Year: B.Tech, 2nd Year
8. Expected Graduation Date: 2028
9. Resume: [Resume](https://drive.google.com/file/d/1hnyt2KPOfiS1uNWjsXIU33ENeKOni_Yh/view?usp=sharing)

---

## Proposal Title

openPIP 2.0: Modern Rewrite of openPIP with Multi-Format Molecular Interaction Ingestion, Admin UX Revamp, and Container-First Deployment

---

## Abstract

openPIP is a valuable open-source platform for hosting and exploring protein-protein interaction datasets. Its current Symfony/PHP implementation has grown over years of incremental feature additions and now mixes routing, parsing, persistence, and presentation logic in ways that increase maintenance cost and slow feature evolution.

This project proposes a full rewrite of openPIP as openPIP 2.0 using modern frameworks and engineering practices:

- Backend: Python API layer (FastAPI) with typed schemas and service boundaries
- Frontend: Next.js 14 + TypeScript for SSR-friendly public portal pages and responsive admin workflows
- Data pipeline: extensible ingestion architecture for PSI-MI TAB and CSV, with a normalized interaction domain model
- Upload/admin UX: drag-and-drop bulk upload, async job processing, progress telemetry, and row-level validation feedback
- Infrastructure: Docker-first local/dev/prod parity, object storage for uploaded files, and CI-enabled quality gates

The outcome is a maintainable, testable, and contributor-friendly platform that preserves openPIP’s core strengths while adding robust support for diverse interaction datasets and richer metadata annotation workflows.

---

## 0.1 Detailed PoC Overview (openpip2_ingestion_poc)

Alongside proposal design, I built and iterated a working proof-of-concept in this workspace under openpip2_ingestion_poc. The PoC validates migration feasibility from legacy Symfony/PHP ingestion behavior to a modern API-plus-worker architecture while preserving operator-critical workflows.

### Scope covered in the PoC

- FastAPI backend with modular routers, service layer, parser layer, and DB abstraction
- Two-phase ingestion workflow: validate first, commit second
- Row-level validation error storage with remediation hints
- Error export endpoint for CSV download
- Parser extensibility through a shared parser contract with multiple implementations
- Duplicate detection and explicit counters (inserted, skipped, failed)
- Legacy compatibility routes for incremental behavior mapping
- Next.js frontend dashboard for upload, status tracking, error review, and commit action
- Progress streaming endpoint for live ingestion updates

### Implemented ingestion workflow

1. Upload request creates a job and stores file metadata.
2. Validation job parses rows and records structured row errors.
3. User reviews validation stage, counters, and error table.
4. Commit job writes valid canonical interactions into persistence.
5. Final status and counters remain queryable for auditability and reproducibility.

This model is safer than single-step blind import and supports real curation practices.

### Technical highlights delivered

- FastAPI + asyncpg job and interaction persistence
- Worker-oriented validate/commit job boundaries
- Upload job status, error list, error export, and events endpoints
- Confidence score normalization support across common input forms
- Parser plugin structure supporting PSI-MI TAB and CSV ingestion
- Hash-based deduplication with inserted-versus-skipped visibility
- Frontend upload manager wired to backend job lifecycle

### Migration value and current limits

What this PoC proves:

- Core ingestion redesign is technically viable and demonstrable end-to-end
- Legacy behavior can be wrapped and migrated incrementally without full big-bang cutover
- Upload observability and data-quality workflows are substantially improved

Current limits:

- Full edge-case parity with all legacy controllers is still pending
- Test coverage should expand further as parity work lands
- Production hardening (beyond dev/demo posture) remains a follow-up track

### Code-level architecture in the PoC

The PoC is intentionally structured around explicit boundaries, not monolithic handlers:

- API bootstrap, lifecycle, and router composition in [openpip2_ingestion_poc/app/main.py](openpip2_ingestion_poc/app/main.py#L26), [openpip2_ingestion_poc/app/main.py](openpip2_ingestion_poc/app/main.py#L61), and [openpip2_ingestion_poc/app/main.py](openpip2_ingestion_poc/app/main.py#L66)
- Upload orchestration in [openpip2_ingestion_poc/app/services/upload_service.py](openpip2_ingestion_poc/app/services/upload_service.py#L43) and commit orchestration in [openpip2_ingestion_poc/app/services/upload_service.py](openpip2_ingestion_poc/app/services/upload_service.py#L103)
- Input hardening for path/query integrity in [openpip2_ingestion_poc/app/services/upload_service.py](openpip2_ingestion_poc/app/services/upload_service.py#L20)
- Error payload normalization for response-model stability in [openpip2_ingestion_poc/app/services/upload_service.py](openpip2_ingestion_poc/app/services/upload_service.py#L27)
- Route-level upload/job APIs in [openpip2_ingestion_poc/app/routers/uploads.py](openpip2_ingestion_poc/app/routers/uploads.py#L20), [openpip2_ingestion_poc/app/routers/uploads.py](openpip2_ingestion_poc/app/routers/uploads.py#L42), and [openpip2_ingestion_poc/app/routers/uploads.py](openpip2_ingestion_poc/app/routers/uploads.py#L67)
- Worker boundaries for validation and commit in [openpip2_ingestion_poc/app/jobs.py](openpip2_ingestion_poc/app/jobs.py#L16) and [openpip2_ingestion_poc/app/jobs.py](openpip2_ingestion_poc/app/jobs.py#L94)
- Deterministic dedupe key generation in [openpip2_ingestion_poc/app/db.py](openpip2_ingestion_poc/app/db.py#L121)
- Row error write path in [openpip2_ingestion_poc/app/db.py](openpip2_ingestion_poc/app/db.py#L296) and CSV export in [openpip2_ingestion_poc/app/db.py](openpip2_ingestion_poc/app/db.py#L420)
- Parser contract and pluggability in [openpip2_ingestion_poc/app/parsers.py](openpip2_ingestion_poc/app/parsers.py#L20) and parser selection in [openpip2_ingestion_poc/app/parsers.py](openpip2_ingestion_poc/app/parsers.py#L281)
- PSI-MI identifier and confidence normalization in [openpip2_ingestion_poc/app/parser.py](openpip2_ingestion_poc/app/parser.py#L17) and [openpip2_ingestion_poc/app/parser.py](openpip2_ingestion_poc/app/parser.py#L42)
- Frontend ingestion control loop with SSE in [openpip2_ingestion_poc/frontend/components/upload-manager.tsx](openpip2_ingestion_poc/frontend/components/upload-manager.tsx#L35), [openpip2_ingestion_poc/frontend/components/upload-manager.tsx](openpip2_ingestion_poc/frontend/components/upload-manager.tsx#L55), and [openpip2_ingestion_poc/frontend/components/upload-manager.tsx](openpip2_ingestion_poc/frontend/components/upload-manager.tsx#L70)

### Legacy-to-modern mapping proof

The migration plan is based on direct responsibility mapping, not abstract equivalence:

- Legacy upload entrypoint [src/AppBundle/Controller/DropzoneController.php](src/AppBundle/Controller/DropzoneController.php#L42) maps to modern compatibility upload endpoint [openpip2_ingestion_poc/app/routers/legacy_compat.py](openpip2_ingestion_poc/app/routers/legacy_compat.py#L29) and core upload service [openpip2_ingestion_poc/app/services/upload_service.py](openpip2_ingestion_poc/app/services/upload_service.py#L43)
- Legacy insert workflow [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L103) maps to queued validate/commit phases in [openpip2_ingestion_poc/app/jobs.py](openpip2_ingestion_poc/app/jobs.py#L16) and [openpip2_ingestion_poc/app/jobs.py](openpip2_ingestion_poc/app/jobs.py#L94)
- Legacy data-manager insertion path [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L337) maps to compatibility route [openpip2_ingestion_poc/app/routers/legacy_compat.py](openpip2_ingestion_poc/app/routers/legacy_compat.py#L108)
- Legacy search route family [src/AppBundle/Controller/SearchController.php](src/AppBundle/Controller/SearchController.php#L43) maps to compatibility search endpoint [openpip2_ingestion_poc/app/routers/legacy_compat.py](openpip2_ingestion_poc/app/routers/legacy_compat.py#L254)

This explicit mapping is important because it reduces regression risk during staged cutover and gives mentors a reviewable trace from old behavior to new service boundaries.

---

## 1. Problem Statement and Why This Project Matters

openPIP currently delivers strong scientific value, but technical debt limits maintainability and extensibility.

### 1.1 Current pain points observed in codebase

- Legacy Symfony kernel + bundle architecture in [app/AppKernel.php](app/AppKernel.php#L6) and [app/AppKernel.php](app/AppKernel.php#L16).
- Routing mixes framework-generated and manually declared routes in [app/config/routing.yml](app/config/routing.yml#L2), with duplicated route keys at [app/config/routing.yml](app/config/routing.yml#L40) and [app/config/routing.yml](app/config/routing.yml#L43).
- Upload and ingestion logic is tightly coupled to controllers and filesystem paths:
  - [src/AppBundle/Controller/DropzoneController.php](src/AppBundle/Controller/DropzoneController.php#L40)
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L103)
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L337)
- PSI-MI tab parsing is embedded inside request handlers with repeated line-based parsing loops:
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L120)
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L452)
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L554)
- Export pathways are controller-heavy and format-specific:
  - [src/AppBundle/Controller/DataDownloadController.php](src/AppBundle/Controller/DataDownloadController.php#L102)
  - [src/AppBundle/Controller/DataDownloadController.php](src/AppBundle/Controller/DataDownloadController.php#L145)
  - [src/AppBundle/Controller/DataDownloadController.php](src/AppBundle/Controller/DataDownloadController.php#L193)
- Search view responsibilities are broad (query parsing, aggregation, response packaging, rendering) in [src/AppBundle/Controller/SearchController.php](src/AppBundle/Controller/SearchController.php#L43) and [src/AppBundle/Controller/SearchController.php](src/AppBundle/Controller/SearchController.php#L114).
- Runtime stack is anchored to older PHP/Apache image baselines in [Docker OpenPIP package/Dockerfile](Docker%20OpenPIP%20package/Dockerfile#L1).

### 1.2 Product-level impact

These technical constraints make it difficult to:

- Add new interaction data formats cleanly
- Provide high-quality upload validation and ingestion observability
- Scale contributor onboarding and review speed
- Maintain confidence during changes (limited isolated service boundaries)

openPIP 2.0 directly addresses these constraints while preserving the core mission: storing, exploring, and sharing interaction data effectively.

---

## 2. Existing System Grounding

I reviewed core surfaces to determine where openPIP 2.0 must preserve behavior and where it must intentionally redesign.

### 2.1 Domain and persistence anchors

The existing schema provides valuable domain concepts that should be preserved and normalized in the new model:

- Interaction table: [openpip.sql](openpip.sql#L296)
- Protein table: [openpip.sql](openpip.sql#L418)
- Dataset table: [openpip.sql](openpip.sql#L160)
- Annotation table: [openpip.sql](openpip.sql#L66)

Entity mappings are currently represented in Doctrine entities such as:

- [src/AppBundle/Entity/Interaction.php](src/AppBundle/Entity/Interaction.php#L1)
- [src/AppBundle/Entity/Upload_Files.php](src/AppBundle/Entity/Upload_Files.php#L1)

### 2.2 Current ingestion and file handling

- Upload endpoint and move-to-directory behavior:
  - [src/AppBundle/Controller/DropzoneController.php](src/AppBundle/Controller/DropzoneController.php#L42)
  - [src/AppBundle/Controller/DropzoneController.php](src/AppBundle/Controller/DropzoneController.php#L57)
- Data manager insert + parse path:
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L103)
  - [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L337)

### 2.3 Current deployment model

- Compose setup with PHP + MySQL services: [Docker OpenPIP package/docker-compose.yml](Docker%20OpenPIP%20package/docker-compose.yml#L8), [Docker OpenPIP package/docker-compose.yml](Docker%20OpenPIP%20package/docker-compose.yml#L20)
- Legacy Apache/PHP image baseline: [Docker OpenPIP package/Dockerfile](Docker%20OpenPIP%20package/Dockerfile#L1)

This grounding informs a migration plan that maps legacy responsibilities to modern service boundaries.

---

## 3. Proposed Architecture for openPIP 2.0

### 3.1 Architecture goals

1. Preserve scientific workflow correctness
2. Separate ingestion, validation, persistence, and query surfaces
3. Enable multi-format support through parser plug-ins
4. Provide first-class upload observability and failure diagnostics
5. Keep deployments reproducible through containerization and CI

### 3.2 Technology stack

- Frontend: Next.js 14 (App Router), TypeScript, TanStack Query, React Hook Form, Zod
- Backend: FastAPI, SQLAlchemy 2.x, Pydantic, Alembic
- Async tasks: ARQ + Redis for async ingestion workers and progress updates
- Database: PostgreSQL as system of record, with optional Apache AGE extension for graph traversals
- File/object storage: MinIO (S3-compatible) for raw uploads and import artifacts
- Auth: Logto (OIDC/OAuth2) for admin/curator/public role flows
- Containerization: Docker Compose for development and reproducible CI
- Deployment target: Coolify (self-hosted PaaS style deployment), with cloud migration path later
- CI: GitHub Actions for lint, type checks, test matrix, and image build smoke checks

### 3.3 Database strategy: PostgreSQL first, Neo4j only if required

I am intentionally proposing PostgreSQL as the single primary database to minimize operational complexity and maximize delivery confidence in GSoC timelines.

- Core plan: relational model + indexed query paths in PostgreSQL
- Graph query plan: optional Apache AGE for openCypher-like traversal on the same database
- Neo4j position: not core for v1 delivery; evaluate only if profiling shows repeated multi-hop graph traversals over very large interaction graphs that cannot meet latency targets in PostgreSQL/AGE

This keeps backup, migration, and contributor setup simple while preserving a clear path to a dedicated graph database if needed.

### 3.4 Service boundaries

- API Gateway Layer: auth, request validation, pagination, filtering
- Upload Service: file intake, checksum, storage abstraction, job enqueue
- Parser Service: PSI-MI TAB parser, CSV parser, validation contracts
- Interaction Service: normalized interaction model orchestration
- Annotation Service: molecule metadata enrichment from public sources
- Export Service: PSI-MI TAB and CSV exports from canonical normalized records
- Search Service: interaction graph retrieval and aggregated query responses

---

## 4. Data Model and Ingestion Design

### 4.1 Canonical normalized model

A canonical interaction record will decouple storage from file format specifics.

High-level entities:

- Molecule (protein/gene/entity abstraction)
- Interaction
- InteractionEvidence
- Dataset
- Annotation
- SourceRecord (raw row provenance)
- UploadJob and UploadJobRowError

This preserves existing concepts from [openpip.sql](openpip.sql#L296) and [openpip.sql](openpip.sql#L418), but adds explicit provenance and validation traces per ingested row.

### 4.2 Multi-format parser contract

Parser plugin interface (conceptual):

- sniff(file) -> confidence
- parse(stream) -> iterator of RawInteractionRecord
- validate(record) -> list of structured validation errors
- transform(record) -> CanonicalInteraction

Initial parsers:

- PsiMiTabParser for PSI-MI TAB
- CsvInteractionParser for curated CSV schema

### 4.3 Validation strategy

- Schema validation: required columns, delimiter checks, encoding checks
- Domain validation: valid interactor identifiers, taxon constraints, score normalization
- Referential validation: dataset and annotation type consistency
- Duplicate and conflict handling: hash-based dedupe plus pair-key conflict resolution

### 4.4 Row-level error UX

Every failed row gets:

- row index
- error code
- human-readable explanation
- remediation hint

This enables practical correction workflows without opaque import failures.

---

## 5. Upload/Admin Experience Redesign

### 5.1 Admin upload workflow

The new interface will replace legacy endpoint-centric flow in [src/AppBundle/Controller/DropzoneController.php](src/AppBundle/Controller/DropzoneController.php#L42) with a job-oriented pipeline:

1. User drags one or many files into uploader
2. Client performs immediate preflight checks (size, extension, delimiter sampling)
3. Backend creates UploadJob, returns job id
4. Worker parses and validates asynchronously
5. UI subscribes to progress updates and displays row-level diagnostics
6. User can accept partial import, download error report, or retry corrected file

### 5.2 UX details

- Bulk upload queue with per-file status
- Live progress bars with stage states: queued, parsing, validating, writing, completed, failed
- Error panel with filter/search by code and row index
- "Download error report" as CSV/JSON
- "Re-run with updated mapping" for CSV column mapping mistakes

### 5.3 Admin controls

- Dataset metadata management
- Annotation type mapping rules
- Controlled vocab mapping for interaction methods and evidence
- Audit trail for uploads and user actions

---

## 6. Metadata and Annotation Enrichment

### 6.1 Target capability

Support importing molecule metadata from public resources (for example UniProt/NCBI-derived identifiers and labels), attached as versioned annotations.

### 6.2 Enrichment architecture

- EnrichmentAdapter interface per provider
- Cached lookup table with TTL and provenance columns
- Rate-limited background enrichment jobs
- Validation to prevent stale/unknown identifier attachment

### 6.3 Safety and reproducibility

- Store source, fetch timestamp, and version snapshot on each annotation
- Support re-enrichment under explicit user action, not silent mutation

---

## 7. API and Frontend Contract

### 7.1 API groups

- Upload APIs: create job, append file, fetch progress, fetch row errors, approve commit
- Interaction APIs: query by molecule, dataset, evidence, status
- Export APIs: PSI-MI TAB export, CSV export, filtered exports
- Metadata APIs: annotation types, enrichment status, mapping dictionaries
- Admin APIs: dataset and portal configuration management

### 7.2 Frontend panes

- Upload Manager
- Dataset Manager
- Search and Results Visualization
- Interaction Detail Drawer
- Export Panel
- Admin Settings

### 7.3 Graph rendering strategy on the website

For PPI network rendering, the primary library will be Cytoscape.js (not D3.js by default):

- Cytoscape.js role: interaction network visualization, node/edge styling, filtering, selection, and layout operations suitable for biological graphs
- D3.js role: optional custom charts (for example upload quality histograms, score distributions, or dataset summary plots), not the primary interaction graph engine
- React Flow role: admin-only workflow views (for ingestion pipeline stages, job states, and provenance flow), separate from biological network rendering

This separation avoids overengineering and picks each library for what it does best.

### 7.4 Search modernization

Legacy behavior in [src/AppBundle/Controller/SearchController.php](src/AppBundle/Controller/SearchController.php#L43) will be reimplemented as API-first composition:

- Query parser in backend service
- Typed API response for proteins/interactions graph payload
- Frontend-only rendering concerns in React

This removes mixed rendering/data logic currently visible in [src/AppBundle/Controller/SearchController.php](src/AppBundle/Controller/SearchController.php#L114).

---

## 8. Migration Plan from Legacy to openPIP 2.0

### 8.1 Migration principles

- Do not big-bang switch without data parity checks
- Build ingestion and query parity harness first
- Maintain reproducible migration scripts and checksums

### 8.2 Incremental migration steps

1. Build canonical schema and migration scripts
2. Import existing SQL snapshot from [openpip.sql](openpip.sql#L1)
3. Backfill canonical model from legacy entities
4. Run parity checks for key queries and export counts
5. Enable dual-run verification on representative datasets
6. Cut over UI and API once parity thresholds pass

### 8.3 Data parity checks

- Total proteins count
- Total interactions count
- Query response equivalence for known test terms
- Export row counts for PSI-MI TAB and CSV

---

## 9. Containerization and DevOps Plan

### 9.1 Why change

Current deployment references older runtime baselines in [Docker OpenPIP package/Dockerfile](Docker%20OpenPIP%20package/Dockerfile#L1). openPIP 2.0 will use dedicated API/worker/frontend containers with explicit health checks and CI verification.

### 9.2 New compose topology

- frontend: Next.js app
- api: FastAPI app
- worker: ARQ worker
- redis: task broker
- postgres: main database
- minio: object storage for uploads

### 9.3 CI pipeline

- backend lint and type checks
- frontend lint and type checks
- unit tests
- integration tests with ephemeral postgres/redis
- container build validation

---

## 10. Testing Strategy

### 10.1 Unit tests

- Parser unit tests (PSI-MI TAB and CSV)
- Domain validator unit tests
- Service-level dedupe/conflict resolution tests
- Annotation mapper tests

### 10.2 Integration tests

- Upload job full lifecycle
- Parser-to-db persistence flow
- Search endpoint response contracts
- Export correctness tests

### 10.3 Regression and data-quality tests

- Golden datasets with expected interaction counts
- Snapshot tests for normalized output records
- Round-trip tests: import -> canonical -> export

### 10.4 Frontend tests

- Component tests for upload queue and progress states
- Interaction/result panel rendering
- Error table filtering and remediation flows

---

## 11. Risks and Mitigation

1. Data model mismatches between PSI-MI TAB and CSV
- Mitigation: canonical transform layer with explicit provenance and per-format adapters

2. Large file ingestion performance bottlenecks
- Mitigation: chunked streaming parser, async jobs, batched writes, indexes

3. Graph query complexity may exceed relational query performance
- Mitigation: start with PostgreSQL indexes/materialized views, then enable Apache AGE for targeted traversals; evaluate Neo4j only if measured latency targets remain unmet

4. Migration regressions
- Mitigation: parity harness, dual-run verification, staged cutover

5. Scope pressure in 12 weeks
- Mitigation: strict core-vs-stretch boundaries, milestone acceptance gates

## 11.1 Explicit Non-Goals for Core Timeline

To keep the core delivery credible within GSoC, the following are intentionally out of core scope unless earlier milestones complete ahead of schedule:

1. Full multi-hop graph analytics engine with custom query language surface
2. Neo4j as a required production dependency
3. Broad metadata federation across many remote providers in core timeline
4. Complex workflow orchestration beyond ingestion and validation jobs
5. Deep visual analytics dashboards beyond core exploration and export workflows

---

## 12. Deliverables

### 12.1 Core deliverables

1. Backend scaffold with typed APIs
- Acceptance criteria: `/health`, `/uploads/jobs`, `/uploads/jobs/{id}`, `/interactions/search`, and export endpoints are implemented and covered by integration tests; OpenAPI docs generated in CI.

2. Upload/admin interface with drag-drop and progress telemetry
- Acceptance criteria: multi-file upload queue supports at least 3 concurrent files; each file exposes stage states (`queued/parsing/validating/writing/completed/failed`) and downloadable row-error report.

3. PSI-MI TAB parser (production-ready)
- Acceptance criteria: parser supports MITAB 2.5/2.6 core 15 columns, handles `|` multi-value fields, stores normalized interactors/evidence, and imports a 100k-row benchmark file with resumable progress tracking.

4. CSV parser with explicit column mapping
- Acceptance criteria: curated CSV template + user mapping UI; validation catches missing mandatory columns and bad identifier patterns; mapped import path writes to same canonical schema as PSI-MI.

5. Canonical interaction model with provenance tracking
- Acceptance criteria: each imported interaction links to `dataset_id`, `source_file`, `source_row`, `parser_version`, and row-level validation status; duplicate detection uses deterministic pair/evidence hash.

6. Export module for PSI-MI TAB and CSV
- Acceptance criteria: filtered exports match canonical query results; parity tests verify row counts and mandatory column coverage against golden fixtures.

7. Containerized development + CI pipeline
- Acceptance criteria: one-command local startup for frontend/api/worker/postgres/redis/minio; CI runs lint, type-check, unit/integration tests, and container build smoke tests.

8. Website graph visualization for PPI exploration
- Acceptance criteria: Cytoscape.js view supports pan/zoom, layout switch, edge filtering by dataset/evidence/status, node search, and export of current subgraph selection.

9. Documentation and contributor onboarding
- Acceptance criteria: setup docs, architecture notes, parser-extension guide, and troubleshooting page for failed imports are complete and reproducible on a clean machine.

### 12.2 Stretch deliverables

1. Additional file formats beyond initial CSV schema
2. Advanced molecule metadata enrichment source federation
3. Performance dashboard for ingestion metrics
4. Neo4j adapter (only if profiling demonstrates PostgreSQL/AGE limits)

---

## 13. Weekly Timeline (12 Weeks)

### Week 1: Community bonding and scope lock

- Finalize acceptance criteria with mentors
- Confirm schema boundaries and migration strategy
- Produce technical design doc

Deliverable: finalized architecture + milestones

### Week 2: Repository scaffolding and infra baseline

- Initialize backend/frontend/worker repos or monorepo structure
- Docker compose for local dev
- CI baseline

Deliverable: runnable skeleton stack

### Week 3: Canonical schema + migrations

- Implement core domain schema
- Alembic migration setup
- Seed scripts and fixture datasets

Deliverable: persistent model foundation

### Week 4: Upload job pipeline core

- File intake endpoints
- Async job queue and progress states
- Job status APIs

Deliverable: asynchronous upload skeleton

### Week 5: PSI-MI TAB parser integration

- Streaming parser for core MITAB columns (A/B interactors, method, publication, taxonomy, confidence)
- Validation engine for column cardinality and identifier formats
- Initial persistence transform path + row error capture

Deliverable: PSI-MI parser alpha with fixture-based tests and resumable job progress

### Week 6: PSI-MI TAB hardening and scale tests

- Multi-value (`|`) and cross-reference field handling
- Duplicate detection, id normalization, and persistence tuning
- Benchmark import testing and failure recovery

Deliverable: production-ready PSI-MI ingestion path

### Week 7: CSV parser + mapping UI (phase 1)

- CSV parser contract implementation
- Column mapping + mandatory field validation
- Bulk upload queue refinements

Deliverable: CSV parser alpha with mapper UI and row-level errors

### Week 8: CSV parser hardening + canonical parity checks

- Canonical transform parity checks (CSV vs PSI-MI ingestion output)
- Conflict resolution and dedupe behavior validation
- Import retries and idempotency checks

Deliverable: production-ready CSV ingestion path

### Week 9: Search/query service migration

- Rebuild query APIs replacing mixed controller rendering
- Graph payload generation
- Pagination/filtering

Deliverable: API-first search endpoint set

### Week 10: Export module and parity checks

- PSI-MI TAB and CSV exports from canonical model
- Export parity tests against legacy behavior

Deliverable: stable export workflows

### Week 11: Frontend UX polish and admin workflows

- Upload error remediation UX
- Dataset/admin management pages
- Accessibility and responsiveness pass

Deliverable: usable admin portal beta

### Week 12: Reliability hardening, docs, and handoff

- Load test ingestion path
- DB index tuning
- Failure/retry behavior hardening
- Contributor guide and architecture docs
- User docs and migration notes
- Final evaluation prep

Deliverable: complete, review-ready openPIP 2.0 package with stabilization evidence

### Post-core stretch window (time permitting)

- External metadata enrichment adapters (UniProt/NCBI federation)
- Neo4j adapter proof-of-concept behind feature flag
- Additional format adapters

---

## 14. Why Me and Execution Confidence

I can execute this project because the work aligns with the exact kind of engineering this rewrite needs:

- Converting monolithic request-layer logic into explicit service boundaries
- Designing parser pipelines that support multiple formats while preserving strict validation
- Building modern admin UIs with clear error states and operational observability
- Delivering in iterative, reviewable milestones instead of big-bang PRs

I have already grounded this proposal in concrete openPIP code surfaces, including ingestion, export, routing, schema, and deployment references:

- [src/AppBundle/Controller/DataController.php](src/AppBundle/Controller/DataController.php#L103)
- [src/AppBundle/Controller/DropzoneController.php](src/AppBundle/Controller/DropzoneController.php#L42)
- [src/AppBundle/Controller/DataDownloadController.php](src/AppBundle/Controller/DataDownloadController.php#L193)
- [src/AppBundle/Controller/SearchController.php](src/AppBundle/Controller/SearchController.php#L43)
- [openpip.sql](openpip.sql#L296)
- [Docker OpenPIP package/docker-compose.yml](Docker%20OpenPIP%20package/docker-compose.yml#L8)

This gives a practical and low-risk path from proposal to implementation.

---

## 15. Implementation Blueprint (Code-Level Sketches)

### 15.1 PSI-MI TAB parser sketch (domain-specific)

```python
from dataclasses import dataclass
from typing import Iterator

MITAB_MIN_COLUMNS = 15

@dataclass
class PsiMiCore15:
    id_a: str
    id_b: str
    alt_id_a: str
    alt_id_b: str
    alias_a: str
    alias_b: str
    detection_method: str
    publication_first_author: str
    publication_id: str
    taxid_a: str
    taxid_b: str
    interaction_type: str
    source_db: str
    interaction_id: str
    confidence: str


def _split_multivalue(value: str) -> list[str]:
    # PSI-MI TAB uses '|' as multi-value separator, '-' for missing values.
    if not value or value == "-":
        return []
    return [v.strip() for v in value.split("|") if v.strip() and v.strip() != "-"]


def _extract_identifier(raw: str) -> tuple[str | None, str | None]:
    # Example token: "uniprotkb:P12345" or "ensembl:ENSP000..."
    token = _split_multivalue(raw)[0] if _split_multivalue(raw) else ""
    if ":" not in token:
        return None, None
    ns, value = token.split(":", 1)
    return ns.lower(), value.strip()


def _parse_confidence(raw: str) -> float | None:
    # Common pattern: "intact-miscore:0.67"
    for token in _split_multivalue(raw):
        if token.startswith("intact-miscore:"):
            try:
                return float(token.split(":", 1)[1])
            except ValueError:
                return None
    return None


def parse_mitab_core_rows(lines: Iterator[str]) -> Iterator[tuple[int, PsiMiCore15]]:
    for row_no, line in enumerate(lines, start=1):
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.rstrip("\n").split("\t")
        if len(cols) < MITAB_MIN_COLUMNS:
            raise ValueError(f"Row {row_no}: expected >=15 columns, found {len(cols)}")

        yield row_no, PsiMiCore15(*cols[:15])
```

### 15.2 Canonical transform sketch for interactor pair + evidence

```python
def to_canonical(row_no: int, rec: PsiMiCore15, dataset_id: int) -> dict:
    ns_a, val_a = _extract_identifier(rec.id_a)
    ns_b, val_b = _extract_identifier(rec.id_b)
    if not val_a or not val_b:
        raise ValueError(f"Row {row_no}: missing canonical interactor ids")

    pair_key = "::".join(sorted([f"{ns_a}:{val_a}", f"{ns_b}:{val_b}"]))
    methods = _split_multivalue(rec.detection_method)
    confidence_score = _parse_confidence(rec.confidence)

    return {
        "dataset_id": dataset_id,
        "pair_key": pair_key,
        "interactor_a_ns": ns_a,
        "interactor_a_id": val_a,
        "interactor_b_ns": ns_b,
        "interactor_b_id": val_b,
        "methods": methods,
        "publication_id": rec.publication_id,
        "interaction_type": rec.interaction_type,
        "confidence_score": confidence_score,
        "source_row": row_no,
    }
```

### 15.3 ARQ ingestion worker signature and progress updates

```python
from arq import create_pool
from arq.connections import RedisSettings


async def ingest_upload_job(ctx, job_id: str, storage_key: str, parser_hint: str | None = None) -> dict:
    db = ctx["db"]
    store = ctx["object_store"]

    await db.jobs.set_stage(job_id, "parsing")
    stream = await store.open_text(storage_key)

    inserted = 0
    failed = 0
    batch: list[dict] = []

    try:
        for row_no, rec in parse_mitab_core_rows(stream):
            await db.jobs.set_progress(job_id, row_no=row_no)
            try:
                canonical = to_canonical(row_no, rec, dataset_id=await db.jobs.dataset_id(job_id))
                batch.append(canonical)
            except Exception as exc:
                failed += 1
                await db.job_errors.add(job_id, row_no=row_no, code="ROW_VALIDATION", message=str(exc))

            if len(batch) >= 1000:
                await db.interactions.bulk_upsert(batch)
                inserted += len(batch)
                batch.clear()
                await db.jobs.set_stage(job_id, "writing")

        if batch:
            await db.interactions.bulk_upsert(batch)
            inserted += len(batch)

        await db.jobs.complete(job_id, inserted=inserted, failed=failed)
        return {"job_id": job_id, "inserted": inserted, "failed": failed}
    except Exception as exc:
        await db.jobs.fail(job_id, reason=str(exc))
        raise


async def enqueue_ingestion(job_id: str, storage_key: str) -> str:
    redis = await create_pool(RedisSettings())
    job = await redis.enqueue_job("ingest_upload_job", job_id, storage_key)
    return job.job_id
```

### 15.4 Data parity harness for migration confidence

```python
def assert_parity(legacy_stats: dict, new_stats: dict) -> None:
    required = ["protein_count", "interaction_count", "dataset_count"]
    for key in required:
        if legacy_stats[key] != new_stats[key]:
            raise AssertionError(
                f"Parity mismatch for {key}: legacy={legacy_stats[key]} new={new_stats[key]}"
            )


def assert_query_fixture_parity(legacy_rows: list[dict], new_rows: list[dict]) -> None:
    legacy_pairs = {tuple(sorted([r["a"], r["b"]])) for r in legacy_rows}
    new_pairs = {tuple(sorted([r["a"], r["b"]])) for r in new_rows}
    if legacy_pairs != new_pairs:
        missing = legacy_pairs - new_pairs
        extra = new_pairs - legacy_pairs
        raise AssertionError(f"Pair mismatch: missing={len(missing)} extra={len(extra)}")
```

### 15.5 Minimal SQL schema fragments for ingestion tracking

```sql
CREATE TABLE upload_jobs (
        id UUID PRIMARY KEY,
        dataset_id BIGINT NOT NULL,
        storage_key TEXT NOT NULL,
        parser_hint TEXT,
        stage TEXT NOT NULL CHECK (stage IN ('queued','parsing','validating','writing','completed','failed')),
        total_rows BIGINT,
        processed_rows BIGINT NOT NULL DEFAULT 0,
        inserted_rows BIGINT NOT NULL DEFAULT 0,
        failed_rows BIGINT NOT NULL DEFAULT 0,
        error_summary TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE upload_job_errors (
        id BIGSERIAL PRIMARY KEY,
        job_id UUID NOT NULL REFERENCES upload_jobs(id) ON DELETE CASCADE,
        source_row BIGINT NOT NULL,
        error_code TEXT NOT NULL,
        error_message TEXT NOT NULL,
        raw_payload JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE interactions (
        id BIGSERIAL PRIMARY KEY,
        dataset_id BIGINT NOT NULL,
        pair_key TEXT NOT NULL,
        interactor_a_ns TEXT NOT NULL,
        interactor_a_id TEXT NOT NULL,
        interactor_b_ns TEXT NOT NULL,
        interactor_b_id TEXT NOT NULL,
        interaction_type TEXT,
        confidence_score DOUBLE PRECISION,
        publication_id TEXT,
        source_file TEXT NOT NULL,
        source_row BIGINT NOT NULL,
        parser_version TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (dataset_id, pair_key, publication_id, source_row)
);

CREATE INDEX idx_interactions_pair_key ON interactions(pair_key);
CREATE INDEX idx_interactions_dataset ON interactions(dataset_id);
```

### 15.6 PSI-MI row example to canonical output example

```text
# MITAB input row (first 15 columns shown)
uniprotkb:P12345\tuniprotkb:Q99999\t-\t-\tgeneA\tgeneB\tpsi-mi:"MI:0018"(two hybrid)|psi-mi:"MI:0407"(direct interaction)\tDoe et al. (2023)\tpubmed:12345678\ttaxid:9606(human)\ttaxid:9606(human)\tpsi-mi:"MI:0915"(physical association)\tpsi-mi:"MI:0469"(IntAct)\tintact:EBI-123456\tintact-miscore:0.78
```

```json
{
    "dataset_id": 42,
    "pair_key": "uniprotkb:P12345::uniprotkb:Q99999",
    "interactor_a_ns": "uniprotkb",
    "interactor_a_id": "P12345",
    "interactor_b_ns": "uniprotkb",
    "interactor_b_id": "Q99999",
    "methods": [
        "psi-mi:\"MI:0018\"(two hybrid)",
        "psi-mi:\"MI:0407\"(direct interaction)"
    ],
    "publication_id": "pubmed:12345678",
    "interaction_type": "psi-mi:\"MI:0915\"(physical association)",
    "confidence_score": 0.78,
    "source_row": 1287
}
```

### 15.7 ARQ worker registration sketch

```python
class WorkerSettings:
        functions = [ingest_upload_job]
        redis_settings = RedisSettings()
        max_jobs = 8
        job_timeout = 60 * 60  # 1 hour for large imports
        keep_result = 3600
```

---

## 16. Final Outcome

By the end of this project, openPIP 2.0 will provide:

- Modern maintainable architecture
- Robust multi-format ingestion (PSI-MI TAB + CSV)
- Strong upload/admin UX with real-time feedback
- Extensible annotation enrichment pipelines
- Containerized, testable, and contributor-friendly workflows

This moves openPIP from legacy maintenance mode to a sustainable platform for future molecular interaction data workflows.

---

## 17. Notes for Customization Before Submission

Replace the About section placeholders with your real profile details, add your past OSS contributions and evidence links, and adjust stack choices if mentors explicitly prefer a different backend/database combination.
