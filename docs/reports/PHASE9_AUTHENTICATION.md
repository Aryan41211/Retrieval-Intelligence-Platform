# Authentication Report — Phase 9

**Project:** Retrieval Intelligence Platform (RIP)
**Phase:** 9 — Enterprise Features
**Module:** `backend/enterprise/` (security, services, routers, config)

---

## 1. Summary

The platform implements a complete, stateless-friendly authentication stack
built on JWTs (PyJWT + bcrypt), with optional OAuth, refresh-token rotation,
password reset, and email verification. All secrets are environment-driven and
validated on startup.

## 2. Mechanisms

### 2.1 JWT (Access + Refresh)
- **Access tokens** (`security.create_access_token`): signed `HS256` JWT
  carrying `sub`, `role`, `permissions`, `iat`, `exp`. TTL configurable via
  `ENTERPRISE_ACCESS_TOKEN_TTL_SECONDS` (default 900s, clamped 60–3600).
- **Refresh tokens** (`security.create_refresh_token`): signed `HS256` JWT with
  a unique `jti` and longer TTL (`ENTERPRISE_REFRESH_TOKEN_TTL_SECONDS`, default
  604800s). Rotation is performed by `services.refresh_tokens`, which issues a
  brand-new access/refresh pair.
- Tokens are verified by `security.decode_token`, which asserts the expected
  `type` claim and raises `PyJWTError` on tamper/expiry.

### 2.2 OAuth
- Google OAuth 2.0 authorization-code flow (`enterprise/oauth.py`):
  `get_authorization_url` builds the consent URL; `exchange_code` swaps the
  code for the user profile via `httpx`.
- **Config-gated:** only active when `ENTERPRISE_OAUTH_ENABLED=true` and Google
  client id/secret/redirect are set. Otherwise `GET /auth/oauth/{provider}/login`
  returns `501 Not Implemented`.
- `services.oauth_login` auto-provisions a verified local account on first login
  (subject to the registration toggle) and issues tokens.

### 2.3 Refresh Tokens
- Stateless JWT refresh with rotation. `POST /auth/refresh` validates the
  refresh token, resolves the user, and returns a new pair. Invalid/expired
  tokens are rejected with `401`.

### 2.4 Password Reset
- `services.create_password_reset_token` mints a single-use token; only a
  **SHA-256 hash** (`security.hash_token`) is stored
  (`PasswordResetToken` table). The raw token is delivered out-of-band (SMTP
  hook in `_send_email`).
- `POST /auth/password-reset/confirm` consumes the token (enforced single-use
  via `used_at`, expiry via `expires_at`) and updates the bcrypt hash. The
  request endpoint is idempotent (never reveals whether an email exists).

### 2.5 Email Verification
- `services.create_email_verification_token` issues a single-use, hashed
  verification token (`EmailVerificationToken`).
- `POST /auth/email/verify` marks the user `is_verified`. When
  `ENTERPRISE_EMAIL_VERIFICATION_REQUIRED=true`, unverified users are rejected
  at login.

### 2.6 Password Storage
- Passwords are hashed with **bcrypt** (`security.hash_password` /
  `verify_password`); comparison is constant-time and tolerant of malformed
  hashes.

## 3. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` | Self-register (returns tokens) |
| POST | `/auth/login` | Password login (email or username) |
| POST | `/auth/refresh` | Rotate token pair |
| POST | `/auth/logout` | Stateless logout (client discards tokens) |
| POST | `/auth/password-reset/request` | Request reset (idempotent) |
| POST | `/auth/password-reset/confirm` | Set new password |
| POST | `/auth/email/verify` | Verify email |
| GET  | `/auth/oauth/{provider}/login` | Begin OAuth (501 if unconfigured) |
| GET  | `/auth/oauth/{provider}/callback` | Complete OAuth |

## 4. Configuration (`enterprise/config.py`)

`ENTERPRISE_JWT_SECRET_KEY` is **mandatory and validated** in production
(`environment == "production"` rejects the dev default). Token TTLs,
registration/verification toggles, OAuth credentials, and SMTP settings are all
environment-driven.

## 5. Test Coverage

- **Unit** (`test_security.py`): bcrypt round-trip, JWT access/refresh
  round-trip, `type` mismatch rejection, tamper rejection, token hashing,
  OAuth state uniqueness.
- **API** (`test_auth_api.py`): register/login/refresh, invalid credentials,
  protected-route enforcement, password-reset full flow, email-verification
  flow, OAuth 501, single-use token enforcement.
- **Service** (`test_services.py`): register/authenticate, token issue/refresh,
  duplicate-registration conflict, password-reset single-use, email-verification
  flow, OAuth unconfigured → 501.

**All authentication tests pass (part of the 65-test enterprise suite).**

## 6. Security Notes

- JWTs are signed, not encrypted; do not place secrets in the payload.
- Refresh tokens are stateless (no server-side revocation list) — acceptable
  for this design; add a denylist if immediate revocation is required.
- Reset/verify tokens are hashed at rest and single-use.
- Rate limiting is enabled by default at the API layer (Phase 8) and disabled
  in the test harness to avoid flakiness.
