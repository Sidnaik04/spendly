# Plan: Step 4 — Profile Page (static design)

## Context
`GET /profile` is still a stub (`app.py:125-127`, returns "Profile page — coming in Step 4"). Spec `.claude/specs/04-profile-page-design.md` asks for a fully designed, login-guarded profile page with **hardcoded** data (user card, summary stats, transaction table, category breakdown), so the UI is settled before Step 5 wires up real queries. Constraints: no DB calls, no inline styles, no hex in the template, category badges via CSS classes, CSS variables only, page styles in their own `.css` file (CLAUDE.md).

## 1. `app.py`
- In the **Helpers** section (after `_validate_login`), add:
  - `_PROFILE_TRANSACTIONS` — 8 hardcoded dicts `{date, description, category, amount}` covering all 7 categories, newest first, ₹ amounts (e.g. Groceries 842.50 Food, Electricity bill 1860.00 Bills, New shoes 2499.00 Shopping…).
  - `_bar_step(pct)` → `max(5, min(100, 5 * round(pct / 5)))` (width-class step).
  - `_profile_placeholder_data()` → returns `{"user": {...}, "stats": {...}, "transactions": [...], "categories": [...]}`.
    - `user`: hardcoded `Demo User`, `demo@spendly.com`, initials `DU`, member since `January 2026` (spec says all hardcoded; Step 5 replaces with a real lookup).
    - `stats` and `categories` are *derived* from the hardcoded list (total, count, top category; per-category `name`, `slug`, `total`, `percent`, `bar_step`, sorted desc) so numbers are self-consistent. Still zero DB access.
- Move `profile()` from the "Placeholder routes" section into "Routes" (after `privacy`):
  ```python
  @app.route("/profile")
  def profile():
      if not session.get("user_id"):
          return redirect(url_for("login"))
      return render_template("profile.html", **_profile_placeholder_data())
  ```
  No new imports needed.

## 2. `static/css/style.css` — category colour variables
Add to `:root` after `--border-soft`: `--cat-food`, `--cat-transport`, `--cat-bills`, `--cat-health`, `--cat-entertainment`, `--cat-shopping`, `--cat-other`, each with a `-light` tint (food can alias `var(--accent-2)` / `var(--accent-2-light)`, other can use `--ink-muted`). Hex only appears in these variable definitions.

## 3. `templates/profile.html` (new)
- `{% extends "base.html" %}`, title `Profile — Spendly`, `{% block head %}` links `url_for('static', filename='css/profile.css')`.
- Structure:
  ```
  section.profile-section > div.profile-container
    header.profile-card: div.profile-avatar (initials) + div.profile-identity
        (h1.profile-name, p.profile-email, p.profile-meta "Member since …")
    section.profile-stats: 3 × div.stat-card (span.stat-label + span.stat-value)
        Total spent ₹{{ "{:,.2f}".format(...) }} | Transactions | Top category
    div.profile-grid
      section.profile-panel  "Recent transactions"
        div.table-scroll > table.txn-table (Date | Description | Category | Amount.num)
        category cell: span.badge.badge-{{ t.category|lower }}
      section.profile-panel  "Spending by category"
        ul.cat-list > li.cat-row: name + "₹amount · N%" +
          div.cat-track > div.cat-bar.cat-bar-{{ c.slug }}.bar-w-{{ c.bar_step }}
  ```
- Literal `₹` character (not `&#8377;`, which would trip a hex check). No `style=`, no `<style>`, `url_for` only. Navbar needs no change — `base.html:22-24` already shows `session.user_name` + Sign out.

## 4. `static/css/profile.css` (new, variables only)
- Layout: `.profile-section` padding, `.profile-container` max-width `var(--max-width)`, column flex with gap.
- User card: `--paper-card` bg, `--border`, `--radius-lg`; 64px round `.profile-avatar` in `--accent` with `--font-display` initials.
- Stats: 3-col grid of `.stat-card` (modelled on `.mock-stat`, style.css:312).
- Panels: `.profile-grid` `2fr 1fr`; `.profile-panel` card with `min-width: 0`.
- Table: `.table-scroll { overflow-x: auto }`, `.txn-table` min-width 520px, muted uppercase `th`, `--border-soft` row borders, `.num` right-aligned tabular nums.
- Badges: `.badge` pill + 7 `.badge-<slug>` rules using `--cat-<slug>` / `--cat-<slug>-light`.
- Bars: `.cat-track` on `--paper-warm`, `.cat-bar-<slug>` ×7, and width classes `.bar-w-5 … .bar-w-100` (20 rules, step 5) — replaces inline widths; exact % shown as text.
- Responsive: ≤900px stats + grid → 1 column; ≤600px tighter padding, user card stacks; at 375px the table scrolls inside its card, no page-level horizontal scroll.

## 5. Tests
- **Remove** stub assertions that will break: `test_profile_still_stub` (`tests/test_auth.py:~204-205`) and `test_stub_routes_unchanged` + its parametrize (`tests/test_registration.py:193-197`).
- `tests/conftest.py`: add `logged_in_client` fixture (sets `user_id`/`user_name` for the demo user via `client.session_transaction()`); still no module-level `app` import.
- **New `tests/test_profile.py`** covering the Definition of done:
  - logged out → 302 to `/login`; logged in → 200, stub text gone
  - user card shows name, email, "Member since"
  - ≥3 `stat-card`s with Total spent / Transactions / Top category and the computed total
  - table with ≥3 `<tbody>` rows; badges render as `badge badge-<slug>`
  - ≥3 `cat-row`s with `bar-w-` classes
  - navbar shows "Demo User" + `/logout` link, no "Sign in"
  - static checks: `profile.html` has no hex, no `style=`/`<style>`, extends `base.html`, no hardcoded `href="/`; `profile.css` linked on the page and contains no hex

## 6. `CLAUDE.md`
- Routes table: `GET /profile` → "Implemented — Step 4: login-guarded; renders `profile.html` with hardcoded placeholder data (real queries in Step 5)".
- Architecture tree: add `profile.css  # Profile-page-only styles`.

## Verification
1. `source venv/bin/activate && pytest` — all green; per CLAUDE.md, have a subagent verify the test results.
2. Dev server (already running on 5001, auto-reloads): open `/profile` logged out → redirected to `/login`; sign in as `demo@spendly.com` / `demo123` → `/profile` shows all four sections, coloured badges, proportional bars, navbar with name + Sign out.
3. DevTools at 900px (single column) and 375px (table scrolls inside card, no page horizontal scroll).
4. `grep -nE '#[0-9a-fA-F]{3,8}\b|style=' templates/profile.html static/css/profile.css` → no matches.
