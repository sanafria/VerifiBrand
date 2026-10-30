# Visual checks (`extraction.visual`)

Returned by `POST /api/scans/upload`. Not saved with the scan yet.

Fields: `processed`, `checks_run`, `findings`, `skipped`, `errors`.
Each finding: category, rule_id, rule_quote, matched_text, explanation, suggested_fix, confidence, status (pass / fail / needs_review).

Checks: colour (Delta-E vs brand palette), clear space, typography (PDF only), layout hierarchy (PDF only).

Rules for anything reading this block:
1. `checks_run` shows what was analysed. `processed=true` only means the file opened.
2. If `processed` is false, never describe or judge the image.
3. Say which checks were skipped or errored. Never imply they passed.
4. Show `needs_review` as "a person must confirm".
5. Empty findings means "no issues in the checks that ran", not "fully compliant".

Plain-language helper: `brandledger_extraction.visual_explainer.explain_visual(visual)`.
Demo files: `backend/extraction_module/demo_creatives/`.
Limits: clear space runs only when a logo is matched with confidence, and automatic matches report needs_review instead of fail. The logo library holds placeholders.
