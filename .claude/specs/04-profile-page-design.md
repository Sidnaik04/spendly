# Spec: Profile Page Design

## Overview
Replace the `/profile` stub with a fully designed profile page that only signed-in users can open. The page shows four sections: a user card (name, email, initials avatar, member-since date), a row of summary stats (total spent, number of transactions, top category), a recent-transactions table, and a spending-by-category breakdown. In this step all data is **hardcoded** placeholder data built in `app.py`, with no database queries. This lets the layout and visual design be settled first. Step 5 then swaps the placeholder data for real queries without touching the template. The step comes after login and logout (Step 3) because the page needs a session to decide who can see it.

## Depends on
- **Step 1 — Database setup**: the seeded demo user (`demo@spendly.com` / `demo123`) and the `CATEGORIES` tuple in `database/db.py` (Food, Transport, Bills, Health, Entertainment, Shopping, Other).
- **Step 2 — Registration**: `app.secret_key`, flash messages, and the test fixtures in `tests/conftest.py`.
- **Step 3 — Login and Logout**: `session["user_id"]` and `session["user_name"]` set on sign-in, and the signed-in navbar in `base.html`.

## Routes
- `GET /profile` — render `profile.html` with hardcoded placeholder data. If nobody is signed in, redirect (302) to `login` — logged-in

No other new routes. `/profile` keeps its existing path and function name, and moves from the "Placeholder routes" section into "Routes" in `app.py`.

## Database changes
No database changes. This step makes no database calls and adds no helpers to `database/db.py`. The existing `users` and `expenses` tables already have everything Step 5 will need.

## Templates
- **Create:**
  - `templates/profile.html` — extends `base.html`, title `Profile — Spendly`, links `profile.css` through `{% block head %}` and `url_for('static', filename='css/profile.css')`. Sections:
    1. **User card**: a round avatar with initials, the name, the email, and "Member since <Month Year>"
    2. **Summary stats**: three stat cards for Total spent (₹, 2 decimals, thousands separators), Transactions (count), and Top category
    3. **Recent transactions**: a table with Date, Description, Category and Amount columns. Category is shown as a coloured badge (`badge badge-<slug>`) and amounts are right-aligned. The table sits in a scroll wrapper so it can scroll sideways on small screens.
    4. **Spending by category**: one row per category with its name, amount, percentage and a horizontal bar. Bar widths use step classes (`bar-w-5` … `bar-w-100`), not inline styles.
- **Modify:**
  - `templates/base.html` — turn the navbar user name into a link: `<a class="nav-user" href="{{ url_for('profile') }}">`, with `aria-current="page"` when `request.endpoint == 'profile'`. Add the pinned Lucide script (`https://unpkg.com/lucide@1.52.0/dist/umd/lucide.min.js`) before `main.js`.

## Files to change
- `app.py`
  - add a hardcoded `_PROFILE_TRANSACTIONS` list (about 8 entries covering all 7 categories, newest first, ₹ amounts)
  - add a `_profile_placeholder_data()` helper that returns `user`, `stats`, `transactions` and `categories`. Derive the stats and category totals from the hardcoded list so the numbers agree with each other. Still no DB access.
  - add a `_bar_step(pct)` helper that rounds a percentage to the nearest step of 5, between 5 and 100
  - replace the `profile()` stub with a login check and `render_template("profile.html", ...)`
  - add an `inr` Jinja template filter (`₹1,234.50`) used for every amount on the page
- `static/css/style.css` — add category colour variables to `:root`: `--cat-food`, `--cat-transport`, `--cat-bills`, `--cat-health`, `--cat-entertainment`, `--cat-shopping`, `--cat-other`, each with a `-light` tint. These variable definitions are the only place hex values may appear. Also add `--shadow-card`, an active-state colour for `a.nav-user[aria-current="page"]`, and keep the user name visible in the navbar at ≤600px.
- `static/js/main.js` — call `lucide.createIcons()` on `DOMContentLoaded`, guarded so pages still work if the CDN fails
- `templates/base.html` — see Templates
- `tests/conftest.py` — add a `logged_in_client` fixture that signs in the demo user through `client.session_transaction()`
- `tests/test_auth.py` and `tests/test_registration.py` — remove the assertions that `/profile` is still a stub
- `CLAUDE.md` — mark `GET /profile` as implemented (Step 4, hardcoded data) in the routes table, and add `profile.css` to the architecture tree

## Files to create
- `templates/profile.html`
- `static/css/profile.css` — styles for the profile page only, using CSS variables only
- `tests/test_profile.py` — tests for the Definition of done items below

## New dependencies
No new pip packages. One pinned CDN script: Lucide icons 1.52.0 from unpkg (never `@latest`).

## Rules for implementation
- No SQLAlchemy or ORMs.
- Parameterised queries only. This step should need none, because it makes no DB calls.
- Passwords are hashed with werkzeug. This step does not touch passwords.
- Use CSS variables. Never hardcode hex values in `profile.css` or in the template. New colours go in as variables in `:root` in `style.css`.
- All templates extend `base.html`.
- No inline `style=` attributes and no `<style>` tags. Page styles go in `static/css/profile.css`.
- Use `url_for()` for every internal link, stylesheet and redirect.
- Category badge and bar colours come from CSS classes keyed by the category slug (`badge-food`, `cat-bar-food`, and so on), not from inline colours.
- Write the ₹ symbol as a literal character, not as an HTML entity.
- Keep the route thin: check the session, get the placeholder data from a helper, render the template.
- Shape the template context the way Step 5 will fill it (`user`, `stats`, `transactions`, `categories`), so Step 5 only changes `app.py`.
- Do not implement Steps 5 and later. No real expense queries, no editing the profile, and no add, edit or delete expense routes.
- Vanilla JS only. The only JS is the Lucide init in `main.js`; no frameworks.
- Use icons sparingly (stat cards, panel headings, member-since line) and size them with CSS.
- Page layout classes use the `profile-` prefix so styles don't leak.
- Never import `app` at module level in `tests/`.

## Definition of done
- [ ] `GET /profile` when signed out redirects (302) to `/login`
- [ ] After signing in as `demo@spendly.com` / `demo123`, `GET /profile` returns 200 and no longer shows "coming in Step 4"
- [ ] The user card shows an initials avatar, the name, the email and a "Member since" line
- [ ] Three stat cards show Total spent (formatted as `₹x,xxx.xx`), Transactions and Top category, and the values match the transactions table
- [ ] The transactions table shows at least 3 rows, each with date, description, a coloured category badge and a right-aligned amount
- [ ] Each category has its own badge colour, and badges for different categories look different
- [ ] The category breakdown shows a row per category, with a bar whose length matches its percentage, sorted from largest to smallest
- [ ] The navbar shows the signed-in user's name and "Sign out", not "Sign in"
- [ ] The navbar name links to `/profile` and is highlighted while on that page
- [ ] Lucide icons render, and the page still renders correctly if the CDN is blocked
- [ ] At 375px the navbar name stays visible (truncated if long) without overflowing
- [ ] At 900px and below, the stats and panels stack into one column
- [ ] At 375px there is no page-level horizontal scroll, and the table scrolls inside its card
- [ ] `profile.html` and `profile.css` contain no hex colours, no `style=` attributes and no `<style>` tags. All links use `url_for()`.
- [ ] `profile.css` is loaded only on the profile page
- [ ] `pytest` passes, including the existing registration and auth tests, using a temporary database
- [ ] The app still starts with `python app.py` on port 5001, and the other routes behave as before
