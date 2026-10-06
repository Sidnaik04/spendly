import os
import re

import pytest
from werkzeug.security import check_password_hash

import database.db as db

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUCCESS_MESSAGE = "Account created — please sign in."
DUPLICATE_MESSAGE = "An account with this email already exists."
REQUIRED_MESSAGE = "All fields are required."
INVALID_EMAIL_MESSAGE = "Please enter a valid email address."
SHORT_PASSWORD_MESSAGE = "Password must be at least 8 characters."


def post_register(client, follow_redirects=False, **overrides):
    data = {
        "name": "Test User",
        "email": "new@example.com",
        "password": "password123",
    }
    data.update(overrides)
    return client.post("/register", data=data, follow_redirects=follow_redirects)


def count_users():
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def read_project_file(*parts):
    with open(os.path.join(PROJECT_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# ------------------------------------------------------------------ #
# GET / templates                                                     #
# ------------------------------------------------------------------ #

def test_get_register_ok(client):
    resp = client.get("/register")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "<form" in body
    assert 'name="password"' in body


def test_form_action_uses_url_for(client):
    body = client.get("/register").get_data(as_text=True)
    assert 'action="/register"' in body

    for template in ("register.html", "login.html"):
        source = read_project_file("templates", template)
        assert 'action="/' not in source
        assert 'href="/' not in source


# ------------------------------------------------------------------ #
# Successful registration                                             #
# ------------------------------------------------------------------ #

def test_valid_registration_creates_user_and_redirects(client):
    before = count_users()
    resp = post_register(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    assert count_users() == before + 1


def test_flash_shown_once(client):
    resp = post_register(client, follow_redirects=True)
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert SUCCESS_MESSAGE in body
    assert 'class="auth-success"' in body

    body_again = client.get("/login").get_data(as_text=True)
    assert SUCCESS_MESSAGE not in body_again


def test_password_is_hashed(client):
    post_register(client)
    row = db.get_user_by_email("new@example.com")
    assert row["password_hash"] != "password123"
    assert check_password_hash(row["password_hash"], "password123")


def test_email_normalised(client):
    post_register(client, email="  Foo@Bar.com ")
    assert db.get_user_by_email("foo@bar.com") is not None


# ------------------------------------------------------------------ #
# Duplicate email                                                     #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("email", ["demo@spendly.com", "DEMO@Spendly.COM"])
def test_duplicate_email_any_case(client, email):
    before = count_users()
    resp = post_register(client, email=email)
    assert resp.status_code == 400
    assert DUPLICATE_MESSAGE in resp.get_data(as_text=True)
    assert count_users() == before


def test_integrity_error_treated_as_duplicate(client, app_module, monkeypatch):
    # Simulate the race: the existence check misses, the insert hits UNIQUE
    monkeypatch.setattr(app_module, "get_user_by_email", lambda email: None)
    before = count_users()
    resp = post_register(client, email="demo@spendly.com")
    assert resp.status_code == 400
    assert DUPLICATE_MESSAGE in resp.get_data(as_text=True)
    assert count_users() == before


# ------------------------------------------------------------------ #
# Validation                                                          #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "overrides",
    [{"name": ""}, {"email": ""}, {"password": ""}, {"name": "   "}],
)
def test_missing_field(client, overrides):
    before = count_users()
    resp = post_register(client, **overrides)
    assert resp.status_code == 400
    assert REQUIRED_MESSAGE in resp.get_data(as_text=True)
    assert count_users() == before


def test_validation_order_required_first(client):
    resp = post_register(client, name="", email="not-an-email")
    assert resp.status_code == 400
    assert REQUIRED_MESSAGE in resp.get_data(as_text=True)


@pytest.mark.parametrize("email", ["foo", "foo@bar", "@bar.com", "foo.bar@baz"])
def test_invalid_email(client, email):
    before = count_users()
    resp = post_register(client, email=email)
    assert resp.status_code == 400
    assert INVALID_EMAIL_MESSAGE in resp.get_data(as_text=True)
    assert count_users() == before


def test_short_password(client):
    before = count_users()
    resp = post_register(client, password="abcdefg")
    assert resp.status_code == 400
    assert SHORT_PASSWORD_MESSAGE in resp.get_data(as_text=True)
    assert count_users() == before


def test_eight_char_password_succeeds(client):
    before = count_users()
    resp = post_register(client, password="abcdefgh")
    assert resp.status_code == 302
    assert count_users() == before + 1


def test_values_preserved_on_error(client):
    resp = post_register(client, password="short")
    body = resp.get_data(as_text=True)
    assert 'value="Test User"' in body
    assert 'value="new@example.com"' in body

    password_tag = re.search(r'<input[^>]*id="password"[^>]*>', body).group(0)
    assert "value=" not in password_tag


# ------------------------------------------------------------------ #
# Styles and regressions                                              #
# ------------------------------------------------------------------ #

def test_auth_success_css_uses_variables():
    css = read_project_file("static", "css", "style.css")
    block = re.search(r"\.auth-success\s*\{([^}]*)\}", css).group(1)
    assert "#" not in block
    assert "var(--" in block


@pytest.mark.parametrize("path", ["/", "/login", "/terms", "/privacy"])
def test_other_pages_still_render(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path, text",
    [("/logout", "coming in Step 3"), ("/profile", "coming in Step 4")],
)
def test_stub_routes_unchanged(client, path, text):
    assert text in client.get(path).get_data(as_text=True)
