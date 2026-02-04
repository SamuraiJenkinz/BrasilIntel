---
phase: 06
plan: 01
subsystem: delivery
tags: [schemas, config, models, email, recipients]

dependency_graph:
  requires: [05-05]
  provides: [EmailRecipients, DeliveryStatus, CC/BCC config, delivery tracking columns]
  affects: [06-02, 06-03, 06-04]

tech_stack:
  added: []
  patterns: [structured recipient handling, delivery status tracking]

key_files:
  created:
    - app/schemas/delivery.py
  modified:
    - app/config.py
    - app/models/run.py

decisions:
  - decision: "EmailRecipients has has_recipients property for validation"
    rationale: "Allow empty configuration but check before sending"
  - decision: "DeliveryStatus uses lowercase values"
    rationale: "Consistent with other enums in project"
  - decision: "_parse_recipient_list as private helper"
    rationale: "DRY principle, used by both get_report_recipients and get_email_recipients"
  - decision: "Nullable delivery columns with defaults"
    rationale: "SQLite auto-migrates without explicit migration script"

metrics:
  duration: ~2 min
  completed: 2026-02-04
---

# Phase 6 Plan 01: Delivery Schemas and Configuration Summary

Extended configuration and models for enhanced email delivery with recipient management and delivery tracking.

## One-Liner
CC/BCC recipient fields in Settings, EmailRecipients schema for structured handling, delivery tracking columns in Run model.

## What Was Built

### Task 1: Delivery Schemas (app/schemas/delivery.py)
- **EmailRecipients**: Pydantic model with to/cc/bcc list fields
  - `has_recipients` property for validation before sending
  - `total_recipients` property for count tracking
  - model_validator for Pydantic v2 compatibility
- **DeliveryStatus**: Enum with pending/sent/failed/skipped values

### Task 2: Settings CC/BCC Fields (app/config.py)
- Added 6 new environment variable fields:
  - `report_recipients_health_cc`, `report_recipients_health_bcc`
  - `report_recipients_dental_cc`, `report_recipients_dental_bcc`
  - `report_recipients_group_life_cc`, `report_recipients_group_life_bcc`
- New `get_email_recipients(category)` method returning EmailRecipients
- Private `_parse_recipient_list()` helper for DRY parsing
- Backward compatibility maintained for `get_report_recipients()`

### Task 3: Run Model Delivery Tracking (app/models/run.py)
- Email delivery tracking: `email_status`, `email_sent_at`, `email_recipients_count`, `email_error_message`
- PDF tracking: `pdf_generated`, `pdf_size_bytes`
- Critical alert tracking: `critical_alert_sent`, `critical_alert_sent_at`, `critical_insurers_count`
- Updated `__repr__` to show email_status when set

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Empty 'to' list allowed in EmailRecipients | Configuration may be incomplete; service layer validates before sending |
| Lowercase DeliveryStatus values | Consistent with InsurerStatus, Sentiment enums |
| Nullable columns with defaults | SQLite handles schema changes automatically |

## Verification Results

All success criteria met:
- [x] EmailRecipients schema exists with to/cc/bcc fields
- [x] DeliveryStatus enum has pending/sent/failed/skipped values
- [x] Settings.get_email_recipients() returns EmailRecipients instance
- [x] Run model has email_status, email_sent_at, pdf_generated, critical_alert_sent columns
- [x] Existing get_report_recipients() still works for backward compatibility

## Commits

| Hash | Description |
|------|-------------|
| eed2793 | feat(06-01): add EmailRecipients and DeliveryStatus schemas |
| 21a77b4 | feat(06-01): extend Settings with CC/BCC recipient fields |
| 8c0998c | feat(06-01): add delivery tracking columns to Run model |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 06-02 (PDF Generation):
- DeliveryStatus enum available for tracking
- Run model has pdf_generated, pdf_size_bytes columns
- EmailRecipients schema ready for email service integration

## Files Changed

| File | Change |
|------|--------|
| app/schemas/delivery.py | Created - EmailRecipients and DeliveryStatus |
| app/config.py | Modified - CC/BCC fields, get_email_recipients method |
| app/models/run.py | Modified - delivery tracking columns |
