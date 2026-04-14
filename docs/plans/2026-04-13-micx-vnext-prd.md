# MicX vNext PRD & Execution Plan

## 1. Objective

Ship the next MicX release as a configurable, operable, Chinese-first admin console built on the current DeerFlow-BY codebase.

This version must deliver:

1. Monitoring and metrics center
2. Remote skill installation
3. Admin backend enhancement
4. Admin-visible configuration center for required system settings
5. Skill Chinese localization support
6. Product rebrand to `MicX`

## 2. Product Goals

### Goal A — Make the system operable

Admins should be able to inspect health, tracing state, core usage metrics, and recent failures without reading raw logs.

### Goal B — Make configuration manageable

Required runtime configuration should be exposed through admin settings rather than remaining hidden only in `config.yaml`, `extensions_config.json`, or env docs.

### Goal C — Make the platform extensible

Skills should be installable remotely through the product UI with metadata, conflict handling, and auditability.

### Goal D — Make the admin console production-ready

Admin flows should cover models, users, workspaces, skills, configs, monitoring, and audit history.

### Goal E — Make the product consistent

The product name, UI copy, and skill presentation should consistently use `MicX` and Chinese-first presentation.

## 3. Confirmed Product Decisions

### 3.1 Sensitive configuration strategy

Confirmed by product owner:

- Admin UI **supports entering plaintext secrets**

Required implementation consequences:

- Secrets must **not** be stored or displayed as raw plaintext after save
- Backend must support encrypted-at-rest storage for admin-managed secrets
- UI must default to masked display
- Reveal actions must be explicit and owner-only
- Audit logs must record configuration changes without storing raw secret values
- Exported configuration and logs must remain redacted

### 3.2 Configuration IA

Split settings into two levels:

- **Personal account settings** — user profile, password, personal preferences
- **Admin configuration center** — system-level settings and operational controls

The existing settings dialog remains for personal preferences. System configuration must move into dedicated admin surfaces.

## 4. Scope

## 4.1 Monitoring & Metrics Center

### User stories

- As an owner, I can see whether the gateway and connected runtime are healthy.
- As an owner, I can see tracing provider status and whether tracing is correctly configured.
- As an owner, I can review key product usage metrics and recent failure summaries.

### Required capabilities

1. **Health overview**
   - Gateway health
   - LangGraph/runtime reachability
   - Config reload status
   - Enabled tracing providers

2. **Metrics overview**
   - Request count
   - Thread count
   - Run count
   - Skill installation count
   - Upload count
   - Artifact generation count
   - Error/failure count
   - Token usage summary where available

3. **Tracing admin**
   - LangSmith enable/configure
   - Langfuse enable/configure
   - Validation feedback before save/reload

4. **Recent issues panel**
   - Recent config errors
   - Recent model test failures
   - Recent skill install failures

### Acceptance criteria

- Owner can open a monitoring page and see live data from backend APIs
- Tracing config can be updated in UI and validated on save
- Pages clearly distinguish `configured`, `enabled`, and `invalid`

## 4.2 Remote Skill Installation

### User stories

- As an owner, I can install a skill from a remote source without uploading it manually into a thread.
- As an owner, I can preview metadata and resolve naming conflicts before install.
- As an owner, I can maintain Chinese-facing metadata for installed skills.

### Required capabilities

1. Install sources
   - `.skill` archive upload
   - remote URL download
   - extensible source abstraction for future Git-based installs

2. Install flow
   - preflight validation
   - metadata preview
   - security scan reuse
   - conflict handling (`cancel`, `replace`, `install as renamed`)

3. Skill metadata management
   - source
   - installed_at
   - version
   - author
   - compatibility
   - localized display name / description

### Acceptance criteria

- Owner can install a skill from URL
- Installed skill appears in list and can be enabled/disabled
- Conflict cases are handled explicitly
- Failure states are user-readable

## 4.3 Admin Backend Enhancement

### User stories

- As an owner, I can manage the full system from one admin console.
- As an owner, I can inspect audit history for sensitive actions.

### Required modules

1. **Admin dashboard**
2. **Configuration center**
3. **Monitoring center**
4. **Skills management**
5. **Enhanced models management**
6. **Enhanced users management**
7. **Enhanced workspaces management**
8. **Audit logs**

### Enhancements by module

#### Models
- delete support
- reload/test history
- last status summary
- default model change visibility

#### Users
- filters by status/role
- last login or last seen when available
- account reset/disable actions as permitted
- audit trail on status changes

#### Workspaces
- counts for members/threads/uploads/agents where feasible
- status controls for active/frozen if storage model supports it

#### Audit logs
- config updates
- model updates
- skill install/enable/disable/edit/rollback
- user status changes
- workspace state changes

### Acceptance criteria

- Owner can navigate all admin modules from one menu
- Sensitive actions write audit records
- Writes are owner-protected on backend routes

## 4.4 Admin Configuration Center

### Objective

Expose required system configuration in the admin UI instead of leaving it hidden in files/docs only.

### Initial config domains in scope

1. **System**
   - log level
   - token usage enabled

2. **Tracing**
   - LangSmith
   - Langfuse

3. **Models**
   - existing model management remains and is linked from config center

4. **Skills**
   - install sources
   - enabled state
   - localized metadata

5. **MCP**
   - server enablement
   - command/url/headers/env
   - OAuth fields

6. **Memory**
   - current configurable controls surfaced through admin-facing settings where system-scoped

7. **Channels**
   - visibility of configured channels and required setup inputs

8. **Branding**
   - name
   - short name
   - tagline
   - support email
   - docs path
   - website path

### Acceptance criteria

- Required config areas are reachable from admin UI
- Save/reload path validates invalid configs and reports clear messages
- Secret fields are masked after save

## 4.5 Skill Chinese Localization

### User stories

- As a Chinese-speaking user, I can understand what each skill does from the UI.
- As an owner, I can edit Chinese display metadata for a skill.

### Required capabilities

- Chinese display name field
- Chinese description field
- fallback to source description if localization absent
- `未翻译` marker when fallback is used

### Acceptance criteria

- Common built-in skills display readable Chinese metadata in UI
- Admin can edit localized metadata for installed/custom skills

## 4.6 MicX Rebrand

### Objective

Replace legacy product-facing names (`DeerFlow`, `BY`, `Mic Service Agent`, `MSA`) with `MicX` in product-facing surfaces for this branch.

### Required surfaces

- brand config
- page titles
- login/workspace/about/admin copy
- skill-related UI copy
- docs/README for this branch

### Acceptance criteria

- No primary user-facing page shows legacy brand names unless intentionally retained in technical migration notes
- Chinese product copy is consistent with MicX naming

## 5. Non-Goals

Not part of this version unless explicitly added later:

- Full marketplace ecosystem
- Billing/subscription system
- Full enterprise RBAC redesign
- Multi-tenant billing
- Large tracing infrastructure rewrite beyond current LangSmith/Langfuse path

## 6. Technical Strategy

### 6.1 Frontend

Use the current admin pages and settings components as the visual/interaction baseline.

Known anchors:

- `frontend/src/components/workspace/admin/models-admin-page.tsx`
- `frontend/src/components/workspace/settings/settings-dialog.tsx`
- `frontend/src/components/workspace/settings/skill-settings-page.tsx`
- `frontend/src/components/workspace/settings/tool-settings-page.tsx`
- `frontend/src/components/workspace/account/account-page.tsx`
- `frontend/src/core/brand/config.ts`
- `frontend/src/core/i18n/locales/zh-CN.ts`

### 6.2 Backend

Extend current gateway router patterns rather than inventing a second admin API style.

Known anchors:

- `backend/app/gateway/routers/models.py`
- `backend/app/gateway/routers/skills.py`
- `backend/app/gateway/routers/mcp.py`
- `backend/packages/harness/deerflow/config/tracing_config.py`
- `backend/packages/harness/deerflow/tracing/factory.py`

### 6.3 Secrets and audit

Implementation must include:

- secret classification
- encryption/decryption service
- masked API response serialization
- audit log append-only records for admin writes

## 7. Delivery Plan

## Phase 1 — Planning docs and target architecture

Deliverables:

- This PRD
- detailed engineering execution checklist
- final architecture decisions for config storage, audit logs, metrics aggregation, and admin IA

## Phase 2 — Admin config foundation

Deliverables:

- backend config center schemas and routes
- secure secret storage foundation
- audit log foundation
- frontend admin config center shell

## Phase 3 — Monitoring center

Deliverables:

- monitoring APIs
- tracing management UI
- health and metrics dashboard

## Phase 4 — Remote skill installation and skills enhancement

Deliverables:

- remote install API
- conflict handling flow
- localized metadata fields and UI

## Phase 5 — Admin enhancements

Deliverables:

- dashboard navigation
- enhanced users/workspaces/models pages
- audit log UI

## Phase 6 — MicX rebrand and content consistency

Deliverables:

- MicX brand config
- localized copy updates
- README/docs updates for this branch

## Phase 7 — Verification and launch readiness

Deliverables:

- diagnostics clean on changed files
- relevant backend/frontend tests passing
- build verification
- launch checklist and rollback notes

## 8. Engineering Task Breakdown

### Backend

1. Add admin config persistence model
2. Add encrypted secret storage utility
3. Add audit log persistence utility
4. Add admin config router(s)
5. Add monitoring and metrics router(s)
6. Add remote skill install router/service extensions
7. Add localized skill metadata persistence
8. Extend models/users/workspaces admin router coverage
9. Add tests for all new admin write paths

### Frontend

1. Add admin dashboard entry points
2. Add config center pages
3. Add monitoring center pages
4. Add remote skill install flows
5. Add audit log pages
6. Add localized skill presentation
7. Split admin settings from personal account settings
8. Rebrand visible product copy to MicX

### Documentation

1. Update root README for MicX branch context
2. Document admin configuration model
3. Document launch checklist
4. Document rollback expectations for admin-managed config

## 9. Release Gates

The release is not complete until all are true:

1. Owner-only admin APIs are permission-checked
2. Secret fields are encrypted at rest and masked in normal reads
3. Audit logs exist for sensitive writes
4. Monitoring and tracing config flows work end-to-end
5. Remote skill install works for URL and archive paths in supported scenarios
6. Skill UI is Chinese-first
7. User-facing product branding is MicX
8. Backend tests and frontend validation pass

## 10. Open Implementation Notes

These require architecture confirmation during execution, not product re-scoping:

- exact persistence file layout for admin-managed secrets and audit logs
- exact health/metrics data sources when certain runtime counters are unavailable
- whether first release of remote skill install supports URL only or URL + upload in one UI

These are engineering decisions and should be settled during implementation with minimal user interruption unless they materially affect product behavior.
