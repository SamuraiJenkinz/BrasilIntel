---
phase: quick
plan: 001
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/classifier.py
  - app/services/reporter.py
autonomous: true

must_haves:
  truths:
    - "Articles with 139K+ character bodies classify successfully without token overflow"
    - "Report generation completes without SQLAlchemy lazy load errors on detached Insurer objects"
    - "Truncation preserves the most relevant portion of the article (the beginning)"
  artifacts:
    - path: "app/services/classifier.py"
      provides: "Description truncation before GPT-4o-mini prompt assembly"
      contains: "MAX_DESCRIPTION_CHARS"
    - path: "app/services/reporter.py"
      provides: "Fixed news_items loading without expunge-then-lazy-load conflict"
  key_links:
    - from: "app/services/classifier.py"
      to: "Azure OpenAI GPT-4o-mini"
      via: "classify_single_news prompt content"
      pattern: "content.*Descri"
    - from: "app/services/reporter.py"
      to: "app/services/reporter.py generate_report / generate_professional_report"
      via: "insurer.news_items access after loading"
      pattern: "insurer\\.news_items"
---

<objective>
Fix two pipeline runtime errors that crash the BrasilIntel daily run:
1. GPT-4o-mini 128K token overflow when classifying articles with very long bodies
2. SQLAlchemy lazy load error when report generation accesses news_items on expunged Insurer objects

Purpose: Restore reliable pipeline execution for daily intelligence runs.
Output: Two patched service files that handle edge cases gracefully.
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/services/classifier.py
@app/services/reporter.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Truncate article descriptions before classification prompt</name>
  <files>app/services/classifier.py</files>
  <action>
In `classify_single_news()` (line ~129), add description truncation BEFORE building the prompt content.

1. Add a module-level constant near the top of the file (after imports, before the class):
   ```python
   # ~50K chars is ~12.5K tokens, leaving ample room for system prompt + title + response
   # within GPT-4o-mini's 128K token limit. Articles front-load the most relevant info.
   MAX_DESCRIPTION_CHARS = 50_000
   ```

2. In `classify_single_news()`, truncate `news_description` before use (between lines 128-129):
   ```python
   # Truncate long descriptions to avoid exceeding model token limits
   if news_description and len(news_description) > MAX_DESCRIPTION_CHARS:
       news_description = news_description[:MAX_DESCRIPTION_CHARS]
       logger.warning(
           f"Truncated description for '{news_title[:80]}' "
           f"from {len(news_description)} to {MAX_DESCRIPTION_CHARS} chars"
       )
   ```

   Note: The logger.warning should log the ORIGINAL length. Store the original length before truncating:
   ```python
   if news_description and len(news_description) > MAX_DESCRIPTION_CHARS:
       original_len = len(news_description)
       news_description = news_description[:MAX_DESCRIPTION_CHARS]
       logger.warning(
           f"Truncated description for '{news_title[:80]}' "
           f"from {original_len} to {MAX_DESCRIPTION_CHARS} chars"
       )
   ```

Do NOT change the prompt structure, the API call, or any other method. Only add the constant and the truncation guard.
  </action>
  <verify>
  - `python -c "from app.services.classifier import ClassifierService, MAX_DESCRIPTION_CHARS; assert MAX_DESCRIPTION_CHARS == 50_000"` succeeds
  - Read the modified file and confirm truncation happens BEFORE `content = f\"Titulo: {news_title}\"`
  - Confirm no other methods were modified
  </verify>
  <done>
  - MAX_DESCRIPTION_CHARS constant exists at module level set to 50000
  - classify_single_news() truncates news_description with a warning log before prompt assembly
  - Original length is captured before truncation for accurate logging
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix SQLAlchemy lazy load error in report generation</name>
  <files>app/services/reporter.py</files>
  <action>
Fix BOTH occurrences of the expunge bug:

**Location 1: `generate_report_from_db()` (lines 199-210)**
**Location 2: `generate_professional_report_from_db()` (lines 458-470)**

For BOTH locations, replace the pattern:
```python
for insurer in insurers:
    db_session.expunge(insurer)
    insurer.news_items = (
        db_session.query(NewsItem)
        .filter(
            NewsItem.insurer_id == insurer.id,
            NewsItem.run_id == run_id
        )
        .all()
    )
```

With this fixed pattern that queries BEFORE expunging:
```python
for insurer in insurers:
    # Query news items while insurer is still bound to session
    run_news_items = (
        db_session.query(NewsItem)
        .filter(
            NewsItem.insurer_id == insurer.id,
            NewsItem.run_id == run_id
        )
        .all()
    )
    # Expunge to detach from session, then assign pre-loaded items
    db_session.expunge(insurer)
    insurer.news_items = run_news_items
```

Update the comments above each block to explain WHY the order matters:
```python
# Load news items for each insurer, then detach from session.
# Order matters: query BEFORE expunge to avoid lazy load errors
# when downstream code accesses insurer.news_items on the detached object.
```

Do NOT change the query logic, the filter conditions, or any other method. Only reorder the expunge/query operations and update comments.
  </action>
  <verify>
  - `python -c "from app.services.reporter import ReporterService"` succeeds (no import errors)
  - Read the modified file and confirm BOTH locations (generate_report_from_db AND generate_professional_report_from_db) have query-before-expunge order
  - Grep for `expunge` in reporter.py and confirm exactly 2 occurrences remain, both AFTER their respective query blocks
  </verify>
  <done>
  - Both generate_report_from_db() and generate_professional_report_from_db() query news_items BEFORE expunging the insurer
  - No lazy load errors possible because news_items are pre-loaded plain Python lists assigned to detached objects
  - Comments explain the ordering constraint
  </done>
</task>

</tasks>

<verification>
- `python -c "from app.services.classifier import ClassifierService; from app.services.reporter import ReporterService; print('Both services import OK')"` passes
- No syntax errors in either file
- The two specific runtime errors described in the bug reports are structurally prevented
</verification>

<success_criteria>
- classifier.py truncates descriptions over 50K chars before prompt assembly, logging a warning
- reporter.py queries news_items before expunging in both report generation methods
- Both files import cleanly with no errors
</success_criteria>

<output>
After completion, create `.planning/quick/001-fix-pipeline-runtime-errors/001-SUMMARY.md`
</output>
