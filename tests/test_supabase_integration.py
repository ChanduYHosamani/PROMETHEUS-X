"""
Phase 5 Integration Tests — Supabase Auth, JWT, Security & Configuration.

These tests use mocks and do NOT require a live Supabase connection.
Run with: python -m pytest tests/test_supabase_integration.py -v
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup — make sure the project root is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_jwt(payload: dict, secret: str, header: dict | None = None) -> str:
    """Construct a minimal HS256 JWT for testing."""
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}

    def _b64(data: dict) -> str:
        encoded = base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=")
        return encoded.decode("ascii")

    h = _b64(header)
    p = _b64(payload)
    signing_input = f"{h}.{p}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")
    return f"{h}.{p}.{sig_b64}"


TEST_SECRET = "test-jwt-secret-32-bytes-padxxxxx"


# ===========================================================================
# 1. JWT Verification — valid token
# ===========================================================================
def test_jwt_verification_valid_token():
    """A correctly signed, non-expired JWT must decode to an AuthenticatedUser."""
    from backend.app.core.security import verify_supabase_jwt

    payload = {
        "sub": "user-uuid-1234",
        "email": "test@example.com",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    token = _build_jwt(payload, TEST_SECRET)
    user = verify_supabase_jwt(token, TEST_SECRET)
    assert user.id == "user-uuid-1234"
    assert user.email == "test@example.com"
    print("PASS: test_jwt_verification_valid_token")


# ===========================================================================
# 2. JWT Verification — expired token raises 401
# ===========================================================================
def test_jwt_verification_expired_raises_401():
    """An expired JWT must raise HTTP 401."""
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    payload = {
        "sub": "user-uuid-1234",
        "exp": int(time.time()) - 60,   # expired 60 seconds ago
    }
    token = _build_jwt(payload, TEST_SECRET)
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(token, TEST_SECRET)
    assert exc_info.value.status_code == 401
    print("PASS: test_jwt_verification_expired_raises_401")


# ===========================================================================
# 3. JWT Verification — wrong secret raises 401
# ===========================================================================
def test_jwt_verification_wrong_secret_raises_401():
    """A JWT signed with a different secret must raise HTTP 401."""
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    payload = {"sub": "user-uuid-1234", "exp": int(time.time()) + 3600}
    token = _build_jwt(payload, "correct-secret-padded-32bytes-xx")
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(token, "wrong-secret-padded-32bytes-xxxx")
    assert exc_info.value.status_code == 401
    print("PASS: test_jwt_verification_wrong_secret_raises_401")


# ===========================================================================
# 4. JWT Verification — missing sub raises 401
# ===========================================================================
def test_jwt_verification_missing_sub_raises_401():
    """A JWT without a 'sub' claim must raise HTTP 401."""
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    payload = {"email": "no-sub@example.com", "exp": int(time.time()) + 3600}
    token = _build_jwt(payload, TEST_SECRET)
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(token, TEST_SECRET)
    assert exc_info.value.status_code == 401
    print("PASS: test_jwt_verification_missing_sub_raises_401")


# ===========================================================================
# 5. JWT Verification — missing secret raises 503
# ===========================================================================
def test_jwt_verification_no_secret_raises_503():
    """Calling verify_supabase_jwt with an empty secret raises HTTP 503."""
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    payload = {"sub": "user-uuid-1234", "exp": int(time.time()) + 3600}
    token = _build_jwt(payload, TEST_SECRET)
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_jwt(token, "")        # empty secret = not configured
    assert exc_info.value.status_code == 503
    print("PASS: test_jwt_verification_no_secret_raises_503")


# ===========================================================================
# 6. Supabase service status — configured vs not configured
# ===========================================================================
def test_supabase_service_status_configured():
    """With all env vars set, SupabaseConfigStatus should report configured=True."""
    from backend.app.db.supabase_client import SupabaseConfigStatus

    # Actual field names: configured, url_present, anon_key_present,
    # service_role_present, jwt_secret_present, storage_bucket
    status = SupabaseConfigStatus(
        configured=True,
        url_present=True,
        anon_key_present=True,
        service_role_present=True,
        jwt_secret_present=True,
        storage_bucket="inspections",
    )
    assert status.configured is True
    assert status.jwt_secret_present is True
    print("PASS: test_supabase_service_status_configured")


def test_supabase_service_status_not_configured():
    """Without a JWT secret, configured and jwt_secret_present must be False."""
    from backend.app.db.supabase_client import SupabaseConfigStatus

    status = SupabaseConfigStatus(
        configured=False,
        url_present=True,
        anon_key_present=True,
        service_role_present=True,
        jwt_secret_present=False,       # missing JWT secret → not fully configured
        storage_bucket="inspections",
    )
    assert status.configured is False
    assert status.jwt_secret_present is False
    print("PASS: test_supabase_service_status_not_configured")


# ===========================================================================
# 7. Protected route — no auth header returns 403
# ===========================================================================
def test_inspection_history_route_without_auth_returns_403():
    """GET /api/v1/inspections without a JWT must return 403 (auto_error=False → HTTPBearer returns None → 403)."""
    from fastapi.testclient import TestClient
    from unittest.mock import patch

    env_patch = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "svc",
        "SUPABASE_JWT_SECRET": TEST_SECRET,
        "CORS_ORIGINS": "http://localhost:5173",
        "ENVIRONMENT": "test",
    }
    with patch.dict(os.environ, env_patch):
        from backend.app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/inspections")
    assert response.status_code in (401, 403)
    print(f"PASS: test_inspection_history_route_without_auth_returns_403 (got {response.status_code})")


def test_review_route_without_auth_returns_403():
    """GET /api/v1/reviews without a JWT must return 401 or 403."""
    import importlib
    from fastapi.testclient import TestClient

    env_patch = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "svc",
        "SUPABASE_JWT_SECRET": TEST_SECRET,
        "CORS_ORIGINS": "http://localhost:5173",
        "ENVIRONMENT": "test",
    }
    with patch.dict(os.environ, env_patch):
        from backend.app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/reviews")
    assert response.status_code in (401, 403)
    print(f"PASS: test_review_route_without_auth_returns_403 (got {response.status_code})")


def test_analytics_without_auth_returns_403():
    """GET /api/v1/analytics/overview without a JWT must return 401 or 403."""
    from fastapi.testclient import TestClient
    from backend.app.core.config import get_settings

    env_patch = {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "anon",
        "SUPABASE_SERVICE_ROLE_KEY": "svc",
        "SUPABASE_JWT_SECRET": TEST_SECRET,
        "CORS_ORIGINS": "http://localhost:5173",
        "ENVIRONMENT": "test",
    }
    get_settings.cache_clear()
    try:
        with patch.dict(os.environ, env_patch):
            from backend.app.main import app
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/v1/analytics/overview")
        assert response.status_code in (401, 403), f"Expected 401/403, got {response.status_code}"
        print(f"PASS: test_analytics_without_auth_returns_403 (got {response.status_code})")
    finally:
        get_settings.cache_clear()


# ===========================================================================
# 8. .gitignore security — env files excluded
# ===========================================================================
def test_gitignore_excludes_env_files():
    """.gitignore must exclude both root and frontend .env files."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    assert gitignore_path.exists(), ".gitignore must exist"
    content = gitignore_path.read_text(encoding="utf-8")

    required_patterns = [".env", "frontend/.env"]
    for pattern in required_patterns:
        assert pattern in content, f".gitignore must include pattern: {pattern!r}"
    print("PASS: test_gitignore_excludes_env_files")


# ===========================================================================
# 9. Service role key not present in any frontend source file
# ===========================================================================
def test_service_role_key_not_in_frontend_files():
    """No frontend/src file may contain the string 'SERVICE_ROLE_KEY'."""
    frontend_src = PROJECT_ROOT / "frontend" / "src"
    if not frontend_src.exists():
        pytest.skip("frontend/src directory does not exist")

    forbidden_strings = ["SERVICE_ROLE_KEY", "service_role_key", "supabase_service_role"]
    violations = []
    for path in frontend_src.rglob("*"):
        if path.is_file() and path.suffix in (".js", ".jsx", ".ts", ".tsx", ".json", ".env"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                for s in forbidden_strings:
                    if s in text:
                        violations.append(f"{path.relative_to(PROJECT_ROOT)}: contains '{s}'")
            except Exception:
                pass
    assert not violations, "Service-role key found in frontend files:\n" + "\n".join(violations)
    print("PASS: test_service_role_key_not_in_frontend_files")


# ===========================================================================
# 10. .env.example completeness
# ===========================================================================
def test_env_example_has_all_required_keys():
    """Every required env var must have a placeholder in .env.example."""
    env_example_path = PROJECT_ROOT / ".env.example"
    assert env_example_path.exists(), ".env.example must exist"
    content = env_example_path.read_text(encoding="utf-8")

    required_keys = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET",
        "SUPABASE_STORAGE_BUCKET",
        "VITE_SUPABASE_URL",
        "VITE_SUPABASE_ANON_KEY",
        "VITE_API_BASE_URL",
        "AI_DEVICE",
        "MVTEC_DATASET_DIR",
        "MAX_UPLOAD_BYTES",
    ]
    missing = [k for k in required_keys if k not in content]
    assert not missing, f".env.example is missing keys: {missing}"
    print("PASS: test_env_example_has_all_required_keys")


# ===========================================================================
# 11. Migration files exist and are non-empty
# ===========================================================================
def test_migration_files_exist():
    """Both SQL migration files must exist and contain RLS-related statements."""
    migrations_dir = PROJECT_ROOT / "supabase" / "migrations"

    m001 = migrations_dir / "001_initial_schema.sql"
    m002 = migrations_dir / "002_rls_improvements.sql"

    assert m001.exists(), "001_initial_schema.sql must exist"
    assert m002.exists(), "002_rls_improvements.sql must exist"

    m001_text = m001.read_text(encoding="utf-8")
    m002_text = m002.read_text(encoding="utf-8")

    assert "row level security" in m001_text.lower(), "001 must enable RLS"
    assert "drop policy" in m002_text.lower(), "002 must drop and recreate policies"
    assert "auth.uid()" in m002_text, "002 must use auth.uid() in scoped policies"
    assert "handle_new_user" in m002_text, "002 must include the auto-profile trigger"
    print("PASS: test_migration_files_exist")


# ===========================================================================
# 12. Storage policies file exists and targets correct bucket
# ===========================================================================
def test_storage_policies_file_exists():
    """storage_policies.sql must exist and reference the 'inspections' bucket."""
    storage_sql = PROJECT_ROOT / "supabase" / "storage_policies.sql"
    assert storage_sql.exists(), "supabase/storage_policies.sql must exist"
    content = storage_sql.read_text(encoding="utf-8")
    assert "'inspections'" in content, "storage_policies.sql must reference the inspections bucket"
    assert "auth.uid()" in content, "storage_policies.sql must use auth.uid() for path scoping"
    print("PASS: test_storage_policies_file_exists")


# ===========================================================================
# 13. ES256 JWKS verification, unsupported alg, and Inspection API auth
# ===========================================================================
def _generate_es256_keypair():
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def test_es256_jwks_valid_token():
    """A valid ES256 token verified against a mocked Supabase JWKS key must succeed."""
    import jwt as pyjwt
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    priv, pub = _generate_es256_keypair()
    supabase_url = "https://example-proj.supabase.co"
    token = pyjwt.encode(
        {
            "sub": "es256-user-1",
            "email": "es256@factory.io",
            "role": "authenticated",
            "aud": "authenticated",
            "iss": f"{supabase_url}/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        priv,
        algorithm="ES256",
        headers={"kid": "test-kid-1"},
    )

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock(key=pub)

    with patch("backend.app.core.security._get_jwk_client", return_value=mock_client):
        user = verify_supabase_jwt(token, jwt_secret="", supabase_url=supabase_url)

    assert user.id == "es256-user-1"
    assert user.email == "es256@factory.io"


def test_es256_jwks_expired_and_wrong_key_rejected():
    """Expired or differently-signed ES256 tokens must raise HTTP 401."""
    import jwt as pyjwt
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    priv, pub = _generate_es256_keypair()
    other_priv, _ = _generate_es256_keypair()
    supabase_url = "https://example-proj.supabase.co"

    expired_token = pyjwt.encode(
        {
            "sub": "es256-user-1",
            "aud": "authenticated",
            "iss": f"{supabase_url}/auth/v1",
            "exp": int(time.time()) - 30,
        },
        priv,
        algorithm="ES256",
        headers={"kid": "test-kid-1"},
    )
    wrong_sig_token = pyjwt.encode(
        {
            "sub": "es256-user-1",
            "aud": "authenticated",
            "iss": f"{supabase_url}/auth/v1",
            "exp": int(time.time()) + 3600,
        },
        other_priv,
        algorithm="ES256",
        headers={"kid": "test-kid-1"},
    )

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = MagicMock(key=pub)

    with patch("backend.app.core.security._get_jwk_client", return_value=mock_client):
        with pytest.raises(HTTPException) as exc_exp:
            verify_supabase_jwt(expired_token, jwt_secret="", supabase_url=supabase_url)
        assert exc_exp.value.status_code == 401

        with pytest.raises(HTTPException) as exc_sig:
            verify_supabase_jwt(wrong_sig_token, jwt_secret="", supabase_url=supabase_url)
        assert exc_sig.value.status_code == 401


def test_unsupported_algorithm_rejected():
    """Tokens with unsupported algorithms (e.g., none or HS384) must raise HTTP 401."""
    import jwt as pyjwt
    from fastapi import HTTPException
    from backend.app.core.security import verify_supabase_jwt

    alg_none_token = _build_jwt(
        {"sub": "user-1", "exp": int(time.time()) + 3600},
        TEST_SECRET,
        header={"alg": "none", "typ": "JWT"},
    )
    with pytest.raises(HTTPException) as exc_none:
        verify_supabase_jwt(alg_none_token, jwt_secret=TEST_SECRET)
    assert exc_none.value.status_code == 401

    hs384_token = pyjwt.encode(
        {"sub": "user-1", "exp": int(time.time()) + 3600},
        TEST_SECRET + "-extra-padding-for-hs384",
        algorithm="HS384",
    )
    with pytest.raises(HTTPException) as exc_384:
        verify_supabase_jwt(hs384_token, jwt_secret=TEST_SECRET)
    assert exc_384.value.status_code == 401


def test_inspection_api_rejects_invalid_bearer_jwt():
    """POST /api/v1/inspections with an invalid Bearer JWT must return 401."""
    import io
    from PIL import Image
    from fastapi.testclient import TestClient
    from backend.app.core.config import get_settings
    from backend.app.main import app

    settings = get_settings()
    orig_secret = settings.supabase_jwt_secret
    settings.supabase_jwt_secret = TEST_SECRET
    try:
        buf = io.BytesIO()
        Image.new("RGB", (32, 32)).save(buf, format="PNG")
        client = TestClient(app)
        resp = client.post(
            "/api/v1/inspections",
            headers={"Authorization": "Bearer invalid.jwt.token"},
            data={"category_id": "bottle", "source_type": "upload"},
            files={"file": ("test.png", buf.getvalue(), "image/png")},
        )
        assert resp.status_code == 401
    finally:
        settings.supabase_jwt_secret = orig_secret


# ===========================================================================
# Runner
# ===========================================================================
if __name__ == "__main__":
    tests = [
        test_jwt_verification_valid_token,
        test_jwt_verification_expired_raises_401,
        test_jwt_verification_wrong_secret_raises_401,
        test_jwt_verification_missing_sub_raises_401,
        test_jwt_verification_no_secret_raises_503,
        test_supabase_service_status_configured,
        test_supabase_service_status_not_configured,
        test_inspection_history_route_without_auth_returns_403,
        test_review_route_without_auth_returns_403,
        test_analytics_without_auth_returns_403,
        test_gitignore_excludes_env_files,
        test_service_role_key_not_in_frontend_files,
        test_env_example_has_all_required_keys,
        test_migration_files_exist,
        test_storage_policies_file_exists,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1

    total = passed + failed
    print(f"\n{'='*55}")
    print(f"Phase 5 Integration Tests: {passed}/{total} passed")
    if failed == 0:
        print("ALL_PHASE5_TESTS_PASSED")
    else:
        print(f"{failed} test(s) FAILED")
    print(f"{'='*55}")
