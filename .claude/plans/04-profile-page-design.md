# Plan: Step 4 — Profile Page Design

## Context
`GET /profile` is still a stub (`app.py:125-127`, returns "Profile page — coming in Step 4", no login guard). `.claude/specs/04-profile-page-design.md` calls for a fully designed, login-guarded profile page with **hardcoded** data: a user card, 3 stat cards, a transactions table and a category breakdown. This settles the UI before Step 5 adds real queries. The design follows `.claude/skills/frontend-design/SKILL.md`: card-based layout, 8px grid, subtle shadows, tabular-nums, table row hover, right-aligned amounts and Lucide icons. It keeps Spendly's existing tokens (green `--accent`, DM Sans / DM Serif Display) rather than the skill's default indigo and system fonts.

**Your decisions (override the spec where they differ):**
1. Lucide icons from a CDN. Pin `https://unpkg.com/lucide@1.52.0/dist/umd/lucide.min.js`, not `@latest`. Check the version exists before implementing.
2. The navbar user name becomes a link to `url_for('profile')`.

**Pitfalls found while researching:**
- At ≤900px, a `1fr` grid track gets stretched by the table's min-width and brings back page-level horizontal scroll. Use `minmax(0, 1fr)` and `min-width: 0` on panels.
- `style.css` (≤600px block, ~:703-704) hides `.nav-user`. Once the name is a link, phones would have no way to reach `/profile`, so the hide rule has to be overridden.
- Two existing tests assert that `/profile` is a stub, and they will break.
- CLAUDE.md lists `landing.css`, but that file doesn't exist.

## 1. `app.py`
**Helpers section** (after `_validate_login`):
- `_PROFILE_USER = {"name": "Demo User", "email": "demo@spendly.com", "member_since": "January 2026"}`
- `_PROFILE_TRANSACTIONS`: 8 dicts `{date, description, category, amount}`, newest first:
  - 2026-10-04 Swiggy dinner order, Food, 642.50
  - 10-03 Electricity bill, Bills, 1450.00
  - 10-02 Metro card recharge, Transport, 500.00
  - 09-30 Running shoes, Shopping, 2499.00
  - 09-28 Pharmacy — vitamins, Health, 385.00
  - 09-27 Movie tickets, Entertainment, 720.00
  - 09-25 Weekly groceries, Food, 1248.75
  - 09-22 Haircut, Other, 300.00
- `@app.template_filter("inr")`: `_format_inr(v)` returns `f"₹{v:,.2f}"`. Step 5 reuses it.
- `_bar_step(pct)` returns `max(5, min(100, 5 * round(pct / 5)))`.
- `_initials(name)`: first letter of up to two words, uppercase ("DU").
- `_profile_placeholder_data()` returns `{user, stats, transactions, categories}`:
  - `transactions`: each entry gets `slug` (the category lowercased) and `date_label` (`"%d %b %Y"`).
  - `categories`: per-category `name, slug, total, percent (round 1dp), bar_step`, sorted by total, largest first.
  - `stats`: `{total, count, top_category = categories[0].name}`.
  - Add `from datetime import datetime`. No DB access.
- Expected values:
  - Total ₹7,745.25, count 8, top category Shopping.
  - Order and bar steps: Shopping 30, Food 25, Bills 20, Entertainment 10, Transport 5, Health 5, Other 5.

**Route.** Remove the stub and add this to "Routes" after `privacy`:
```python
@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("profile.html", **_profile_placeholder_data())
```

## 2. `static/css/style.css`
- **`:root`** (after `--border-soft`). This is the only place new hex values go:
  - `--shadow-card: 0 1px 2px rgba(15,15,15,.04), 0 1px 3px rgba(15,15,15,.06);`
  - Category colours and `-light` tints:

    | Variable | Colour | `-light` |
    |---|---|---|
    | `--cat-food` | `#c17f24` | `#fdf3e3` |
    | `--cat-transport` | `#2f6f9f` | `#e7f0f7` |
    | `--cat-bills` | `#6b5ca5` | `#efedf7` |
    | `--cat-health` | `#2a8577` | `#e5f3f0` |
    | `--cat-entertainment` | `#c4553a` | `#fbebe6` |
    | `--cat-shopping` | `#a0527a` | `#f7eaf1` |
    | `--cat-other` | `#6b6b6b` | `#f0ede6` |
- **Navbar:**
  - Add `transition: color .2s` to the base `.nav-user` rule. It must stay var()-only for `test_nav_user_css_uses_variables`.
  - Add `.nav-links a.nav-user[aria-current="page"] { color: var(--accent); }`.
- **≤600px block:** replace `.nav-user { display: none; }` with:
  - `.navbar { padding: 0 1rem; }`
  - `.nav-links { gap: 1rem; }`
  - `.nav-links a.nav-user { display: block; max-width: 6rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }`

## 3. `templates/base.html`
- **Line ~23:** change the name to `<a href="{{ url_for('profile') }}" class="nav-user"{% if request.endpoint == 'profile' %} aria-current="page"{% endif %}>{{ session.user_name }}</a>`.
- **Before the `main.js` script:** add the pinned Lucide `<script>`.

## 4. `static/js/main.js`
```js
document.addEventListener("DOMContentLoaded", function () {
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
```
The guard means the page still works if the CDN fails.

## 5. `templates/profile.html` (new)
- **Setup:** extends `base.html`. Title is `Profile — Spendly`. The `head` block links `url_for('static', filename='css/profile.css')`.
- **Structure:**
```
section.profile-page > div.profile-container
  header.profile-card
    div.profile-avatar[aria-hidden] {{ user.initials }}
    div.profile-identity: h1.profile-name, p.profile-email,
      p.profile-meta (calendar-days icon) "Member since {{ user.member_since }}"
  section.profile-stats[aria-label="Spending summary"]
    3 × article.profile-stat: span.profile-stat-icon (wallet | receipt | tag)
      + span.profile-stat-label + span.profile-stat-value
      values: {{ stats.total|inr }} | {{ stats.count }} | {{ stats.top_category }}
  div.profile-grid
    section.profile-panel[aria-labelledby=profile-txn-heading]
      header.profile-panel-head: history icon, h2 "Recent transactions",
        span.profile-panel-note "{{ stats.count }} entries"
      div.profile-table-scroll > table.profile-table
        thead: Date | Description | Category | th.profile-num Amount
        tbody {% for t %}: td.profile-date <time datetime=t.date>t.date_label</time>,
          description, span.badge.badge-{{ t.slug }}, td.profile-num {{ t.amount|inr }}
        {% else %} td.profile-empty colspan=4 "No transactions yet."
    section.profile-panel[aria-labelledby=profile-cat-heading]
      header: chart-pie icon, h2 "Spending by category"
      ul.profile-cat-list > li.profile-cat-row
        div.profile-cat-head: .profile-cat-name, .profile-cat-amount (|inr), .profile-cat-pct
        div.profile-cat-track > div.cat-bar.cat-bar-{{ c.slug }}.bar-w-{{ c.bar_step }}
```
- **Icons:** `<span class="profile-icon" aria-hidden="true"><i data-lucide="…"></i></span>`.
- **Rules:**
  - Write a literal `₹`, not `&#8377;`.
  - No `style=`, no `<style>`, no hex, and `url_for` only.

## 6. `static/css/profile.css` (new, var() only, 8px grid)
1. **Page:**
   - `.profile-page`: padding 3rem 2rem 4rem.
   - `.profile-container`: `max-width: var(--max-width)`, centred, flex column, gap 1.5rem.
2. **Cards:** `.profile-card, .profile-stat, .profile-panel` share `--paper-card` background, `1px solid var(--border)`, `--radius-md` and `--shadow-card`.
3. **Icons:**
   - `.profile-icon`: 20px inline-flex, `--accent`, `flex-shrink: 0`.
   - `.profile-icon-sm`: 16px.
   - `svg { width: 100%; height: 100% }`. The box is pre-sized so nothing shifts when icons load.
4. **User card:**
   - Flex row, gap 1.5rem, padding 1.5rem 2rem.
   - Avatar: 64px circle, `--accent` background, `--paper-card` text, display font at 1.5rem.
   - Name: display font, 2rem.
   - Email: `--ink-muted`, `overflow-wrap: anywhere`.
   - Meta line: `--ink-faint`, 0.875rem, inline-flex.
5. **Stats:**
   - `.profile-stats`: `repeat(3, minmax(0, 1fr))`, gap 1.5rem.
   - `.profile-stat`: grid `auto 1fr`, padding 1.5rem.
   - Icon tile: 40px, `--accent-light` background, `--radius-sm`, spans 2 rows.
   - Label: 0.875rem, `--ink-muted`.
   - Value: 1.5rem, weight 600, tabular-nums.
6. **Grid and panels:**
   - `.profile-grid`: `minmax(0, 2fr) minmax(0, 1fr)`, gap 1.5rem, `align-items: start`.
   - `.profile-panel`: padding 1.5rem, `min-width: 0`.
   - Panel head: flex, gap 0.5rem. Title: body font, 1.125rem, weight 600. Note sits right in `--ink-faint`.
7. **Table:**
   - `.profile-table-scroll { overflow-x: auto }`.
   - `.profile-table`: 100% wide, min-width 560px, collapsed borders, 0.875rem.
   - `th`: 0.75rem uppercase, letter-spacing .06em, `--ink-muted`, `--border` bottom border.
   - `td`: padding .75rem 1rem, `--border-soft` bottom border.
   - Last row has no border.
   - Row hover: `--paper` background with a .15s transition.
   - `.profile-num`: right-aligned, tabular-nums, nowrap.
   - `.profile-date`: muted, nowrap.
8. **Category colours:**
   - Fallback: `.badge, .cat-bar { --cat: var(--cat-other); --cat-light: var(--cat-other-light) }`.
   - Then 7 rules like `.badge-food, .cat-bar-food { --cat: var(--cat-food); --cat-light: var(--cat-food-light) }`.
9. **Badge:**
   - Pill (999px), padding .25rem .75rem, 0.75rem, weight 600.
   - `--cat-light` background with `--ink-soft` text (AA contrast).
   - `::before` adds an 8px dot in `--cat`.
10. **Category list:**
    - Flex column, gap 1rem. Head row: name, amount (`margin-left: auto`), pct (`--ink-faint`, min-width 3rem).
    - Track: .5rem high, `--paper-warm`, rounded.
    - `.cat-bar`: `background: var(--cat)`.
11. **Bar widths:** `.bar-w-5 … .bar-w-100`, 20 rules.
12. **Motion:** `@keyframes profile-bar-grow` (scaleX 0 → 1) on `.cat-bar`, turned off under `prefers-reduced-motion`.
13. **Responsive:**
    - ≤900px: stats and grid become `minmax(0, 1fr)`.
    - ≤600px:
      - Page padding 2rem 1rem.
      - User card stacks.
      - Name at 1.5rem.
      - Panel and stat padding 1rem.
    - At 375px: no page-level horizontal scroll, and the table scrolls inside its card.

## 7. Tests
- **`tests/conftest.py`:** add a `logged_in_client` fixture. It uses `client.session_transaction()` to set `user_id` and `user_name` from `db.get_user_by_email("demo@spendly.com")`, with no module-level `app` import.
- **`tests/test_auth.py`:**
  - Delete `test_profile_still_stub` (:204-205).
  - Add `profile.html` to the `test_templates_use_url_for` parametrize list.
- **`tests/test_registration.py`:** repoint `test_stub_routes_unchanged` (:193-198) at `/expenses/add` (Step 7), `/expenses/1/edit` (Step 8) and `/expenses/1/delete` (Step 9).
- **New `tests/test_profile.py`:**
  - **Access:**
    - Signed out: 302 to `/login`.
    - Signed in: 200, title "Profile — Spendly", stub text gone.
  - **User card:** "DU", "Demo User", email and "Member since" are present.
  - **Stat cards:** three `profile-stat` cards showing "₹7,745.25", 8 and "Shopping".
  - **Data consistency** via `app_module._profile_placeholder_data()`:
    - Sum of amounts equals the total; count equals the number of transactions.
    - Top category is the largest; categories are sorted largest first.
    - Percentages add up to ~100 (±0.5).
    - All 7 categories appear; every `bar_step` is in `range(5, 101, 5)`.
  - **Helpers:**
    - `_bar_step` parametrized: (0, 5), (3.87, 5), (24.4, 25), (32.3, 30), (97.6, 100), (150, 100).
    - `inr` filter: `1234.5` gives `"₹1,234.50"`.
  - **Table:**
    - 8 tbody rows.
    - `badge badge-<slug>` for all 7 slugs.
    - At least 9 `profile-num` cells.
    - The `cat-bar-(\w+) bar-w-(\d+)` order and steps match the expected values.
  - **Navbar:**
    - On `/profile`: "Demo User", `href="/profile"`, `aria-current="page"` and "Sign out" are present; "Sign in" is not.
    - On `/`: the profile link is there with no `aria-current`.
  - **Assets:**
    - `profile.css` loads on `/profile` but not on `/` or `/login`.
    - Lucide is pinned (`lucide@1.`, no `@latest`) and loads before `main.js`.
    - `main.js` has `DOMContentLoaded` and `createIcons`.
    - The `wallet`, `receipt`, `tag` and `calendar-days` icons are present.
  - **Static checks:**
    - `profile.html` extends `base.html`; has no hex, `style=`, `<style`, `href="/` or `&#8377;`; and contains a literal ₹.
    - `profile.css` has no hex, uses `var(--` and has the `bar-w-5` and `bar-w-100` rules.
    - The `:root` block in `style.css` has `--cat-<slug>` and `-light` for all 7 slugs.

## 8. Spec and CLAUDE.md updates
- **`.claude/specs/04-profile-page-design.md`:**
  - **Templates:** `base.html` is now modified (Lucide script and the profile link on the name).
  - **Files to change:** add `static/js/main.js` and the `inr` filter; `style.css` also gets `--shadow-card` and the navbar tweaks.
  - **New dependencies:** "No pip packages; one pinned CDN script (Lucide 1.52.0)".
  - **Rules:**
    - Only JS is the Lucide init.
    - Use few icons, sized in CSS.
    - Layout classes use the `profile-` prefix.
  - **Definition of done:**
    - The navbar name links to `/profile` and is highlighted there.
    - Icons render, and the page still works without JS.
    - The name stays visible at 375px.
- **`CLAUDE.md`:**
  - **Routes table:** `GET /profile` → "Implemented — Step 4: login-guarded; `profile.html` with hardcoded `_profile_placeholder_data()` (real queries Step 5)".
  - **Architecture tree:** add `profile.css`; mark `landing.css` as not yet created; describe `main.js` as Lucide init.
  - **Tech constraints:** Lucide is the only third-party script, loaded from a pinned unpkg URL.
  - **Warnings:** category colours live only in `:root`; use the `inr` filter for every ₹ amount.

## Verification
1. `source venv/bin/activate && pytest`: all green. Then, per CLAUDE.md, have a subagent re-run the tests and check the results.
2. `grep -nE '#[0-9a-fA-F]{3,8}\b|style=|<style' templates/profile.html static/css/profile.css` should return nothing.
3. Dev server on 5001:
   - Signed out, `/profile` should redirect to `/login`.
   - Sign in as `demo@spendly.com` / `demo123`, then click the name in the navbar.
   - The name should be green, the four sections should show icons, and the badges should look different from each other.
   - The bars should run Shopping → Other.
4. DevTools:
   - At 900px everything should be one column.
   - At 375px, `document.documentElement.scrollWidth === 375`, the table scrolls inside its card, and the navbar name shows with an ellipsis.
   - Block unpkg: the page should still render with no console errors.
5. `/`, `/login`, `/register`, `/terms` and `/privacy` should still return 200, and the expense stubs should be unchanged.
