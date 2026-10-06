import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
SLUGS = ["food", "transport", "bills", "health", "entertainment", "shopping", "other"]

EXPECTED_BARS = [
    ("shopping", "30"),
    ("food", "25"),
    ("bills", "20"),
    ("entertainment", "10"),
    ("transport", "5"),
    ("health", "5"),
    ("other", "5"),
]


def read_project_file(*parts):
    with open(os.path.join(PROJECT_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def nav_html(body):
    return re.search(r"<nav.*?</nav>", body, re.S).group(0)


def profile_body(logged_in_client):
    return logged_in_client.get("/profile").get_data(as_text=True)


# ------------------------------------------------------------------ #
# Access                                                              #
# ------------------------------------------------------------------ #

def test_profile_redirects_when_signed_out(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_renders_when_signed_in(logged_in_client):
    resp = logged_in_client.get("/profile")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "coming in Step 4" not in body
    assert "<title>Profile — Spendly</title>" in body


# ------------------------------------------------------------------ #
# Content                                                             #
# ------------------------------------------------------------------ #

def test_user_card(logged_in_client):
    body = profile_body(logged_in_client)
    assert re.search(r'class="profile-avatar"[^>]*>DU<', body)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "Member since" in body


def test_stat_cards(logged_in_client):
    body = profile_body(logged_in_client)
    assert body.count('class="profile-stat"') == 3
    for label in ("Total spent", "Transactions", "Top category"):
        assert label in body
    assert '<span class="profile-stat-value">₹7,745.25</span>' in body
    assert '<span class="profile-stat-value">8</span>' in body
    assert '<span class="profile-stat-value">Shopping</span>' in body


def test_stats_consistent_with_transactions(app_module):
    data = app_module._profile_placeholder_data()
    transactions = data["transactions"]
    categories = data["categories"]
    stats = data["stats"]

    assert stats["total"] == pytest.approx(sum(t["amount"] for t in transactions))
    assert stats["count"] == len(transactions)
    assert stats["top_category"] == max(categories, key=lambda c: c["total"])["name"]
    assert [c["total"] for c in categories] == sorted(
        (c["total"] for c in categories), reverse=True
    )
    assert sum(c["percent"] for c in categories) == pytest.approx(100, abs=0.5)
    assert {c["slug"] for c in categories} == set(SLUGS)
    assert all(c["bar_step"] in range(5, 101, 5) for c in categories)


@pytest.mark.parametrize(
    "pct, step",
    [(0, 5), (3.87, 5), (24.4, 25), (32.3, 30), (97.6, 100), (100, 100), (150, 100)],
)
def test_bar_step(app_module, pct, step):
    assert app_module._bar_step(pct) == step


def test_inr_filter(app):
    assert app.jinja_env.filters["inr"](1234.5) == "₹1,234.50"


def test_transactions_table(logged_in_client):
    body = profile_body(logged_in_client)
    tbody = re.search(r"<tbody>(.*?)</tbody>", body, re.S).group(1)
    assert tbody.count("<tr>") == 8
    for slug in SLUGS:
        assert f'class="badge badge-{slug}"' in body


def test_amounts_right_aligned(logged_in_client):
    body = profile_body(logged_in_client)
    # One header cell plus one cell per transaction
    assert body.count('class="profile-num"') >= 9


def test_category_breakdown_sorted(logged_in_client):
    body = profile_body(logged_in_client)
    assert re.findall(r"cat-bar-(\w+) bar-w-(\d+)", body) == EXPECTED_BARS


# ------------------------------------------------------------------ #
# Navbar                                                              #
# ------------------------------------------------------------------ #

def test_navbar_signed_in_on_profile(logged_in_client):
    nav = nav_html(profile_body(logged_in_client))
    assert "Demo User" in nav
    assert 'href="/profile"' in nav
    assert 'aria-current="page"' in nav
    assert "Sign out" in nav
    assert "Sign in" not in nav


def test_nav_user_links_to_profile_elsewhere(logged_in_client):
    nav = nav_html(logged_in_client.get("/").get_data(as_text=True))
    assert 'href="/profile"' in nav
    assert "aria-current" not in nav


# ------------------------------------------------------------------ #
# Assets and static checks                                            #
# ------------------------------------------------------------------ #

def test_profile_css_only_on_profile(client, logged_in_client):
    assert "css/profile.css" in profile_body(logged_in_client)
    for path in ("/", "/login"):
        assert "css/profile.css" not in client.get(path).get_data(as_text=True)


def test_lucide_pinned_and_initialised():
    base = read_project_file("templates", "base.html")
    assert "unpkg.com/lucide@1." in base
    assert "lucide@latest" not in base
    assert base.index("lucide.min.js") < base.index("js/main.js")

    main_js = read_project_file("static", "js", "main.js")
    assert "DOMContentLoaded" in main_js
    assert "createIcons" in main_js


def test_profile_icons_present(logged_in_client):
    body = profile_body(logged_in_client)
    for icon in ("wallet", "receipt", "tag", "calendar-days"):
        assert f'data-lucide="{icon}"' in body


def test_profile_template_static_rules():
    source = read_project_file("templates", "profile.html")
    assert source.lstrip().startswith('{% extends "base.html" %}')
    assert not HEX.search(source)
    assert "style=" not in source
    assert "<style" not in source
    assert 'href="/' not in source
    assert "&#8377;" not in source


def test_profile_css_uses_variables_only():
    css = read_project_file("static", "css", "profile.css")
    assert not HEX.search(css)
    assert "var(--" in css
    assert ".bar-w-5 " in css
    assert ".bar-w-100 " in css


def test_category_vars_in_root():
    css = read_project_file("static", "css", "style.css")
    root = re.search(r":root\s*\{([^}]*)\}", css).group(1)
    for slug in SLUGS:
        assert f"--cat-{slug}:" in root
        assert f"--cat-{slug}-light:" in root
