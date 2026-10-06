import os
import re
from urllib.parse import urlparse

import pytest

import database.db as db

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"
DEMO_NAME = "Demo User"

INVALID_MESSAGE = "Invalid email or password."
REQUIRED_MESSAGE = "Email and password are required."
LOGOUT_MESSAGE = "You've been signed out."


def post_login(client, follow_redirects=False, **overrides):
    data = {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
    data.update(overrides)
    return client.post("/login", data=data, follow_redirects=follow_redirects)


def sign_in(client):
    with client.session_transaction() as sess:
        sess["user_id"] = db.get_user_by_email(DEMO_EMAIL)["id"]
        sess["user_name"] = DEMO_NAME


def nav_html(body):
    return re.search(r"<nav.*?</nav>", body, re.S).group(0)


def read_project_file(*parts):
    with open(os.path.join(PROJECT_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


# ------------------------------------------------------------------ #
# Login                                                               #
# ------------------------------------------------------------------ #

def test_get_login_ok(client):
    resp = client.get("/login")
    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "<form" in body
    assert 'name="password"' in body


def test_login_success_redirects_home_and_sets_session(client):
    resp = post_login(client)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/"
    with client.session_transaction() as sess:
        assert sess["user_id"] == db.get_user_by_email(DEMO_EMAIL)["id"]
        assert sess["user_name"] == DEMO_NAME


def test_login_normalises_email(client):
    resp = post_login(client, email="  DEMO@Spendly.com ")
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/"


def test_login_wrong_password(client):
    resp = post_login(client, password="wrong-password")
    assert resp.status_code == 401
    assert INVALID_MESSAGE in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_unknown_email(client):
    resp = post_login(client, email="nobody@example.com")
    assert resp.status_code == 401
    assert INVALID_MESSAGE in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": ""},
        {"password": ""},
        {"email": "", "password": ""},
        {"email": "   "},
    ],
)
def test_login_missing_fields(client, overrides):
    resp = post_login(client, **overrides)
    assert resp.status_code == 400
    assert REQUIRED_MESSAGE in resp.get_data(as_text=True)


def test_failed_login_keeps_email(client):
    body = post_login(client, password="wrong-password").get_data(as_text=True)
    assert f'value="{DEMO_EMAIL}"' in body
    password_input = re.search(r'<input[^>]*name="password"[^>]*>', body).group(0)
    assert "value=" not in password_input


def test_register_then_login(client):
    client.post(
        "/register",
        data={"name": "New User", "email": "new@example.com", "password": "password123"},
    )
    resp = post_login(client, email="new@example.com", password="password123")
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/"


@pytest.mark.parametrize("method", ["get", "post"])
@pytest.mark.parametrize("path", ["/login", "/register"])
def test_auth_pages_redirect_home_when_signed_in(client, path, method):
    sign_in(client)
    # Valid form data proves the redirect happens before any form handling
    data = {"name": "Other User", "email": "other@example.com", "password": "password123"}
    before = db.get_user_by_email("other@example.com")
    resp = getattr(client, method)(path, data=data)
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/"
    assert before is None and db.get_user_by_email("other@example.com") is None


# ------------------------------------------------------------------ #
# Navbar                                                              #
# ------------------------------------------------------------------ #

def test_navbar_signed_in(client):
    sign_in(client)
    nav = nav_html(client.get("/").get_data(as_text=True))
    assert DEMO_NAME in nav
    assert "Sign out" in nav
    assert 'href="/logout"' in nav
    assert "Sign in" not in nav
    assert "Get started" not in nav


def test_navbar_signed_out(client):
    nav = nav_html(client.get("/").get_data(as_text=True))
    assert "Sign in" in nav
    assert "Get started" in nav
    assert "Sign out" not in nav


# ------------------------------------------------------------------ #
# Logout                                                              #
# ------------------------------------------------------------------ #

def test_logout_clears_session_and_flashes(client):
    post_login(client)
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "user_name" not in sess

    body = client.get("/login").get_data(as_text=True)
    assert LOGOUT_MESSAGE.replace("'", "&#39;") in body
    assert 'class="auth-success"' in body

    body_again = client.get("/login").get_data(as_text=True)
    assert LOGOUT_MESSAGE.replace("'", "&#39;") not in body_again


def test_logout_when_signed_out(client):
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


# ------------------------------------------------------------------ #
# Static checks and regressions                                       #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("template", ["base.html", "login.html"])
def test_templates_use_url_for(template):
    source = read_project_file("templates", template)
    assert 'action="/' not in source
    assert 'href="/' not in source


def test_nav_user_css_uses_variables():
    css = read_project_file("static", "css", "style.css")
    block = re.search(r"\.nav-user\s*\{([^}]*)\}", css).group(1)
    assert "#" not in block
    assert "var(--" in block


def test_uses_temp_db(app_module):
    assert not db.DB_PATH.endswith("spendly.db")


@pytest.mark.parametrize("path", ["/", "/register", "/terms", "/privacy"])
def test_other_pages_still_render(client, path):
    assert client.get(path).status_code == 200


def test_profile_still_stub(client):
    assert "coming in Step 4" in client.get("/profile").get_data(as_text=True)
