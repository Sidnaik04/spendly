# Step 5 — Profile backend connection

## Context
The `/profile` page from Step 4 shows hardcoded data built in `app.py` (`_PROFILE_USER`, `_PROFILE_TRANSACTIONS`, `_profile_placeholder_data()`). Spec 05 replaces it with real per-user queries. The user decided the following, overriding parts of the spec:
- Helpers go in **`database/db.py`**, as CLAUDE.md requires, not in a new `database/queries.py`.
- The seed total is **₹314.84**. The spec's ₹346.24 is wrong.
- Category percentages are **integers that sum to exactly 100**. The largest category absorbs any rounding remainder.

Expected seed results for the demo user:
- **Category totals:** Bills 120.75, Shopping 64.20, Transport 45.00, Health 30.00, Food 20.90, Entertainment 18.99, Other 15.00
- **Percentages:** 38 / 20 / 14 / 10 / 7 / 6 / 5
- **Bar steps:** 40 / 20 / 15 / 10 / 5 / 5 / 5
- **Top category:** Bills
- **Transactions:** 8

## 1. `database/db.py`: four helpers (after `create_user`)
Follow the existing pattern: `conn = get_db()`, `try/finally: conn.close()`, `?` placeholders only (including `LIMIT ?`), and aggregation in SQL. Import `datetime`.

- **`get_user_by_id(user_id)`** returns `{name, email, member_since}` or `None`.
  - `member_since` is `users.created_at[:10]` formatted as `"%B %Y"`.
- **`get_summary_stats(user_id)`** returns `{total_spent, transaction_count, top_category}`.
  - Query: `COALESCE(SUM(amount),0)` and `COUNT(*)`.
  - Top category: `GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1`.
  - With no expenses it returns `{0, 0, "—"}`.
- **`get_recent_transactions(user_id, limit=10)`** returns a list of `{date, description, category, amount}`, ordered `date DESC, id DESC`.
- **`get_category_breakdown(user_id)`** returns a list of `{name, amount, pct}`, ordered by `amount DESC, name ASC`.
  - Set `pct = int(round(amount / grand * 100))`, then `items[0]["pct"] += 100 - sum(pcts)`.
  - Return `[]` if there are no rows or `grand == 0`.

## 2. `app.py`: thin mapping layer
- Delete `_PROFILE_USER`, `_PROFILE_TRANSACTIONS` and `_profile_placeholder_data`.
- Keep the `inr` filter, `_bar_step` and `_initials`. The template keys stay unchanged.
- Extend the `database.db` import.
- Add `_profile_context(user_id)`. It returns `None` if the user is missing; otherwise:
  - `user`: the db result plus `initials`
  - `stats`: `{total, count, top_category}`, mapped from `total_spent` and `transaction_count`
  - `transactions`: each row plus `slug` (`category.lower()`) and `date_label` (`"%d %b %Y"`)
  - `categories`: `{name, slug, total=amount, percent=pct, bar_step=_bar_step(pct)}`
- In `profile()`:
  - Keep the session guard.
  - If `_profile_context` returns `None`, run `session.clear()` and redirect to `login`.
  - Otherwise render `profile.html` with the context.

## 3. `templates/profile.html`
- **Panel note:** show `Latest {{ transactions|length }} of {{ stats.count }}` when the list is capped; otherwise `{{ stats.count }} entries`.
- **Category list:** add `{% else %}<li class="profile-cat-row profile-empty">No spending yet.</li>`. This uses the existing `.profile-empty` style, so no CSS changes.

## 4. Tests
- **`tests/test_profile.py`:**
  - `₹7,745.25` becomes `₹314.84`.
  - The `Shopping` top category becomes `Bills`.
  - `EXPECTED_BARS` uses the real bar steps above.
  - Rewrite `test_stats_consistent_with_transactions` against `_profile_context(demo_id)`. The percentages must sum to exactly 100.
- **New `tests/test_backend_connection.py`:** uses the conftest fixtures and never imports `app` at module level.
  - **Unit tests:**
    - each helper on the demo user and on an empty new user
    - `get_user_by_id(99999)` returns `None`
    - exact newest-first order and the id tie-break, using explicit dates (seed dates collide when `today.day <= 7`)
    - the default limit of 10 and `limit=3`
    - 10/10/10 gives percentages 34/33/33
    - user isolation: one user's expenses never show in another user's results
  - **Route tests:**
    - signed out: 302 to `/login`
    - demo user: 200 with name, email, ₹314.84, 8, Bills, 7 bars, and dates non-increasing
    - empty user: ₹0.00, 0, —, and both empty states
    - deleted-user session: 302 to `/login` and the session is cleared
    - 12 expenses: "Latest 10 of 12" and 10 table rows

## 5. Docs
- **`CLAUDE.md`:** mark `/profile` as Step 5 (real data) in the routes table, and add the four helpers to the db.py helpers list.
- **Spec 05:** change 346.24 to 314.84, change `queries.py` to `db.py`, and note the two template tweaks.

## Verification
- Run `pytest` (full suite), then `pytest tests/test_backend_connection.py tests/test_profile.py -v`. Per CLAUDE.md, a subagent verifies the test results.
- Run `grep -n "_PROFILE_\|_profile_placeholder_data\|queries.py\|346.24" app.py tests CLAUDE.md .claude/specs/05-*`. Expect no hits.
- Run `python app.py` (port 5001) and check:
  - Signed in as demo@spendly.com / demo123: ₹314.84 · 8 · Bills, and 7 category bars.
  - A newly registered user: ₹0.00 · 0 · —, with both empty states.
