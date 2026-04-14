# MicX vNext Execution Checklist

## Milestone 1 — Foundation

- [ ] Finalize target storage for admin-managed config and secrets
- [ ] Finalize audit log schema and persistence path
- [ ] Finalize admin navigation information architecture
- [ ] Create backend router/module skeletons
- [ ] Create frontend admin page skeletons

## Milestone 2 — Secure config center

- [ ] Implement backend config read API with masked secret serialization
- [ ] Implement backend config write API with validation and reload flow
- [ ] Implement encryption/decryption service for admin-entered secrets
- [ ] Implement audit records for config changes
- [ ] Implement frontend config center sections: system, tracing, branding, MCP, skills, channels

## Milestone 3 — Monitoring center

- [ ] Implement health summary API
- [ ] Implement metrics aggregation API
- [ ] Implement recent failures/events API
- [ ] Implement tracing settings UI and validation UX
- [ ] Implement monitoring dashboard cards and detail views

## Milestone 4 — Skills vNext

- [ ] Implement remote URL install backend flow
- [ ] Reuse security scanning during remote install
- [ ] Implement conflict resolution policy in API and UI
- [ ] Persist install metadata and localized metadata
- [ ] Add install dialog and status UX in admin skills page

## Milestone 5 — Admin enhancements

- [ ] Add admin dashboard landing page
- [ ] Enhance models management with delete/history/status fields
- [ ] Enhance users management with filtering/status actions
- [ ] Enhance workspaces management with summary stats/status actions
- [ ] Add audit log list/filter page

## Milestone 6 — Localization and MicX rebrand

- [ ] Replace product-facing legacy names with MicX
- [ ] Update brand config defaults
- [ ] Update Chinese product copy in key admin/workspace/settings flows
- [ ] Add Chinese-first skill metadata rendering
- [ ] Update branch README/docs references

## Milestone 7 — Verification

- [ ] Run backend diagnostics and targeted tests
- [ ] Run frontend diagnostics/typecheck/build
- [ ] Run integration smoke tests for owner flows
- [ ] Verify secret masking/audit behavior manually
- [ ] Produce launch checklist and rollback notes
