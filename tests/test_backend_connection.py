import re
from datetime import date

import pytest

import database.db as db

# Every test depends on the app_module fixture (directly or via client
# fixtures) so DB_PATH points at a fresh temp database.


def _demo_id():
    return db.get_user_by_email("demo@spendly.com")["id"]


def _new_user(email="empty@example.com"):
    return db.create_user("Empty User", email, "password123")


def _add_expense(user_id, amount, category, expense_date, description):
    conn = db.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
    finally:
        conn.close()


def _sign_in(client, user_id, name="Empty User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


def _tbody(body):
    return re.search(r"<tbody>(.*?)</tbody>", body, re.S).group(1)


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_profile_fields(app_module):
    user = db.get_user_by_id(_demo_id())
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["member_since"] == date.today().strftime("%B %Y")
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", user["member_since"])
    assert "password_hash" not in user


def test_get_user_by_id_unknown_returns_none(app_module):
    assert db.get_user_by_id(99999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_summary_stats_for_seed_user(app_module):
    stats = db.get_summary_stats(_demo_id())
    assert stats["total_spent"] == pytest.approx(314.84)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_for_empty_user(app_module):
    stats = db.get_summary_stats(_new_user())
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_recent_transactions_for_seed_user(app_module):
    rows = db.get_recent_transactions(_demo_id())
    assert len(rows) == 8
    for row in rows:
        assert set(row) == {"date", "description", "category", "amount"}
    dates = [row["date"] for row in rows]
    assert dates == sorted(dates, reverse=True)


def test_recent_transactions_newest_first_with_id_tiebreak(app_module):
    user_id = _new_user()
    _add_expense(user_id, 10, "Food", "2026-01-05", "middle")
    _add_expense(user_id, 10, "Food", "2026-01-09", "newest")
    _add_expense(user_id, 10, "Food", "2026-01-01", "oldest")
    _add_expense(user_id, 10, "Food", "2026-01-05", "middle-later")

    descriptions = [row["description"] for row in db.get_recent_transactions(user_id)]
    assert descriptions == ["newest", "middle-later", "middle", "oldest"]


def test_recent_transactions_for_empty_user(app_module):
    assert db.get_recent_transactions(_new_user()) == []


def test_recent_transactions_limit(app_module):
    user_id = _new_user()
    for day in range(1, 13):
        _add_expense(user_id, 5, "Other", f"2026-02-{day:02d}", f"item {day}")

    assert len(db.get_recent_transactions(user_id)) == 10
    assert len(db.get_recent_transactions(user_id, limit=3)) == 3


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_category_breakdown_for_seed_user(app_module):
    items = db.get_category_breakdown(_demo_id())
    assert [i["name"] for i in items] == [
        "Bills", "Shopping", "Transport", "Health", "Food", "Entertainment", "Other",
    ]
    assert [i["pct"] for i in items] == [38, 20, 14, 10, 7, 6, 5]
    assert all(isinstance(i["pct"], int) for i in items)
    assert sum(i["pct"] for i in items) == 100
    amounts = [i["amount"] for i in items]
    assert amounts == sorted(amounts, reverse=True)
    assert items[4]["amount"] == pytest.approx(20.90)


def test_category_breakdown_largest_absorbs_remainder(app_module):
    user_id = _new_user()
    _add_expense(user_id, 10, "Food", "2026-03-01", "a")
    _add_expense(user_id, 10, "Bills", "2026-03-02", "b")
    _add_expense(user_id, 10, "Health", "2026-03-03", "c")

    items = db.get_category_breakdown(user_id)
    assert [i["pct"] for i in items] == [34, 33, 33]
    assert sum(i["pct"] for i in items) == 100


def test_category_breakdown_for_empty_user(app_module):
    assert db.get_category_breakdown(_new_user()) == []


def test_users_data_is_isolated(app_module):
    user_id = _new_user()
    _add_expense(user_id, 999.00, "Food", "2026-04-01", "Big dinner")

    stats = db.get_summary_stats(user_id)
    assert stats["total_spent"] == pytest.approx(999.00)
    assert stats["transaction_count"] == 1
    assert [r["description"] for r in db.get_recent_transactions(user_id)] == ["Big dinner"]

    demo = db.get_summary_stats(_demo_id())
    assert demo["total_spent"] == pytest.approx(314.84)
    assert demo["transaction_count"] == 8
    assert "Big dinner" not in [
        r["description"] for r in db.get_recent_transactions(_demo_id())
    ]


# ------------------------------------------------------------------ #
# GET /profile                                                        #
# ------------------------------------------------------------------ #

def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_shows_seed_user_data(logged_in_client):
    resp = logged_in_client.get("/profile")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert '<span class="profile-stat-value">₹314.84</span>' in body
    assert '<span class="profile-stat-value">8</span>' in body
    assert '<span class="profile-stat-value">Bills</span>' in body
    assert len(re.findall(r"cat-bar-\w+ bar-w-\d+", body)) == 7
    dates = re.findall(r'<time datetime="([\d-]+)">', _tbody(body))
    assert len(dates) == 8
    assert dates == sorted(dates, reverse=True)


def test_profile_empty_state_for_new_user(client):
    _sign_in(client, _new_user())
    resp = client.get("/profile")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert '<span class="profile-stat-value">₹0.00</span>' in body
    assert '<span class="profile-stat-value">0</span>' in body
    assert '<span class="profile-stat-value">—</span>' in body
    assert "No transactions yet." in body
    assert "No spending yet." in body
    assert "cat-bar-" not in body


def test_profile_clears_session_for_deleted_user(client):
    _sign_in(client, 99999, name="Ghost")
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_profile_caps_transactions_at_ten(client):
    user_id = _new_user()
    for day in range(1, 13):
        _add_expense(user_id, 5, "Other", f"2026-02-{day:02d}", f"item {day}")
    _sign_in(client, user_id)

    body = client.get("/profile").get_data(as_text=True)
    assert "Latest 10 of 12" in body
    assert _tbody(body).count("<tr>") == 10
    assert '<span class="profile-stat-value">12</span>' in body
