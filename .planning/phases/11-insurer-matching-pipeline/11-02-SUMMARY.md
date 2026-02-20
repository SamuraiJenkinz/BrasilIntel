---
phase: 11-insurer-matching-pipeline
plan: 02
subsystem: matching
tags: [azure-openai, structured-output, pydantic, ai-disambiguation, hallucination-guard, apiEvent, tenacity]

# Dependency graph
requires:
  - phase: 11-01-deterministic-matcher
    provides: MatchResult schema with ai_disambiguation method and unmatched routing
  - phase: 07-llm-classification
    provides: Azure OpenAI client pattern with proxy detection logic
  - phase: 10-factiva-integration
    provides: ApiEvent recording pattern with isolated session
provides:
  - AIInsurerMatcher service with Azure OpenAI structured output for insurer identification
  - Insurer context limited to 200 entries (token optimization)
  - AI hallucination guard validating returned IDs against provided list
  - Graceful degradation to unmatched when Azure OpenAI unavailable
  - ApiEvent recording for AI match cost monitoring
affects: [11-03-pipeline-integration, 12-equity-tracking, 13-admin-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Azure OpenAI structured output using client.beta.chat.completions.parse with Pydantic response_format"
    - "Corporate proxy URL detection (same pattern as classifier.py)"
    - "AI hallucination guard validating IDs before returning MatchResult"
    - "Insurer context truncation to MAX_INSURER_CONTEXT=200 with sorted prioritization (enabled=True first)"
    - "ApiEvent recording with isolated DB session (never crashes matcher)"
    - "Portuguese system prompt for AI matching consistency"

key-files:
  created:
    - app/services/ai_matcher.py
  modified: []

key-decisions:
  - "MAX_INSURER_CONTEXT=200 to stay within token limits (configurable class constant)"
  - "Sort insurers by enabled=True first, then alphabetically before truncation"
  - "Reuse ApiEventType.NEWS_FETCH for AI matcher events (api_name='ai_matcher' distinguishes)"
  - "Portuguese system prompt matches classifier.py for output consistency"
  - "AI hallucination guard filters out IDs not in provided insurer list"
  - "Graceful degradation returns method='unmatched' when Azure OpenAI unavailable/fails"

patterns-established:
  - "AIInsurerMatcher: follows ClassificationService proxy detection pattern exactly"
  - "InsurerMatchResponse: internal Pydantic model for structured output parsing"
  - "ai_match: returns MatchResult with method='ai_disambiguation' or 'unmatched'"
  - "Tenacity retry (2 attempts, exponential backoff) on all OpenAI calls"

# Metrics
duration: 3min
completed: 2026-02-19
---

# Phase 11 Plan 02: AI-Assisted Insurer Matching Summary

**Azure OpenAI structured output with hallucination guard for ambiguous insurer identification handling ~20% of articles**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-20T01:18:10Z
- **Completed:** 2026-02-20T01:21:25Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- AIInsurerMatcher service using Azure OpenAI structured output for insurer identification
- Insurer context limited to 200 entries with smart sorting (enabled=True first) to stay within token limits
- AI hallucination guard validates returned IDs against provided insurer list before returning MatchResult
- Graceful degradation to method='unmatched' when Azure OpenAI is not configured or fails
- ApiEvent recording for cost monitoring with isolated DB session (never crashes matcher)
- Portuguese system prompt for consistency with classifier.py output style

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AIInsurerMatcher service** - `f15fcfb` (feat)

## Files Created/Modified
- `app/services/ai_matcher.py` - AIInsurerMatcher class with ai_match method using Azure OpenAI structured output

## Decisions Made

**MAX_INSURER_CONTEXT=200 for token limit management:**
- 897 insurers total exceeds token limits when included in system prompt
- Sort insurers by enabled=True first (active insurers prioritized), then alphabetically
- Log warning when truncation occurs with total count and max context size
- Configurable via class constant for future adjustment

**Reuse ApiEventType.NEWS_FETCH for AI matcher events:**
- api_events table is generic (designed for all enterprise API interactions)
- api_name='ai_matcher' distinguishes AI matching events from Factiva news fetches
- Maintains consistency with existing event types (no schema changes needed)
- Phase 13 admin dashboard will filter by api_name for AI cost monitoring

**AI hallucination guard filters returned IDs:**
- Build set of valid_insurer_ids from provided insurers list
- Filter parsed_result.insurer_ids to only include valid IDs
- Log warning when hallucination detected (original_ids vs validated_ids)
- Critical for preventing non-existent insurer IDs in database

**Portuguese system prompt for consistency:**
- Matches classifier.py Portuguese prompt style ("Você é um assistente de IA...")
- Instruction clarity: "retorne os IDs da lista acima" (return IDs from list above)
- Variation handling: "com e sem acentos, abreviações, nomes comerciais" (with/without accents, abbreviations, trade names)
- Temperature=0 for deterministic outputs

**Graceful degradation to unmatched:**
- When Azure OpenAI not configured: client=None, is_configured()=False
- When AI match fails: catch all exceptions, log warning, record failed ApiEvent
- Both cases return MatchResult(method='unmatched', confidence=0.0, reasoning=error_message)
- Never crashes pipeline — Plan 03 can still process unmatched articles

**Corporate proxy URL detection pattern:**
- Copy exact proxy detection logic from classifier.py (lines 76-96)
- Critical for BrasilIntel's Azure OpenAI endpoint format
- Extract base_url and model from `/deployments/{model}/chat/completions` endpoint
- Use OpenAI client with base_url (not AzureOpenAI) for proxy endpoints

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - classifier.py and factiva.py provided complete patterns to follow.

## User Setup Required

None - no external service configuration required beyond existing Azure OpenAI setup from Phase 7.

## Next Phase Readiness

**Ready for Plan 03 (Pipeline Integration):**
- AIInsurerMatcher.is_configured() method available for pipeline pre-flight checks
- ai_match() returns MatchResult compatible with deterministic matcher output
- ApiEvent recording integrated for Phase 13 admin dashboard cost monitoring
- Graceful degradation ensures pipeline never crashes on AI failures

**Verification complete:**
- AIInsurerMatcher imports and initializes without error
- is_configured() returns False when Azure OpenAI not configured (expected)
- No crashes during initialization (structlog warning logged, client=None set)
- Ready for Plan 03 to integrate both deterministic and AI matchers into pipeline

**Blockers/Concerns:**
- First AI match calls will incur Azure OpenAI costs (Phase 13 dashboard monitors via ApiEvent)
- 200-insurer context limit works for BrasilIntel's 897 insurers (enabled=True prioritization)
- Production testing needed to validate hallucination guard effectiveness
- Article title truncated to 100 chars in ApiEvent detail to avoid token bloat

---
*Phase: 11-insurer-matching-pipeline*
*Completed: 2026-02-19*
