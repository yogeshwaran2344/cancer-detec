"""
Authentication & Cryptographic Session Security Layer
Enforces server-side user identity verification and record ownership authorization.
Prevents unauthenticated cross-user data access and tampering.
"""

import hmac
import hashlib
import base64
import json
import time
import os
from typing import Optional, Dict, Any
from fastapi import Header, Query, HTTPException, status
from pydantic import BaseModel


SECRET_KEY = os.environ.get("PATHOGUARD_AUTH_SECRET", "pathoguard_secure_local_hmac_secret_2026_clinical")
SESSION_EXPIRATION_SECONDS = 86400 * 7  # 7-day session validity


class AuthenticatedUser(BaseModel):
    user_id: str
    is_authenticated: bool = True
    auth_method: str = "bearer_token"
    issued_at: int = 0
    expires_at: int = 0


def generate_session_token(user_id: str, validity_seconds: int = SESSION_EXPIRATION_SECONDS) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 session token for a given user.
    """
    now = int(time.time())
    payload = {
        "uid": user_id,
        "iat": now,
        "exp": now + validity_seconds
    }
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip('=')
    
    # Calculate HMAC signature
    sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"pgs_{payload_b64}.{sig}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies token signature and expiration. Returns payload dict if valid, else None.
    """
    if not token or not token.startswith("pgs_"):
        return None
        
    core = token[4:]
    if "." not in core:
        return None
        
    payload_b64, signature = core.split(".", 1)
    
    # Re-compute expected signature
    expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return None
        
    try:
        # Restore padding if needed
        padding_needed = (4 - len(payload_b64) % 4) % 4
        padded_b64 = payload_b64 + ('=' * padding_needed)
        payload_bytes = base64.urlsafe_b64decode(padded_b64.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))
        
        # Check expiration
        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None
            
        return payload
    except Exception:
        return None


def get_current_authenticated_user(
    authorization: Optional[str] = Header(None, description="Bearer session token")
) -> AuthenticatedUser:
    """
    FastAPI dependency that extracts and validates the caller's server-side identity.
    Enforces that authorization headers provide authentic signed tokens.
    Rejects caller-controlled query parameters as an identity grant.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please obtain a signed session token via /api/v1/auth/session and provide 'Authorization: Bearer <token>' header."
        )

    raw_token = authorization.split("Bearer ", 1)[1].strip()
    verified = verify_session_token(raw_token)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, tampered, or expired session token. Please re-authenticate."
        )

    return AuthenticatedUser(
        user_id=verified["uid"],
        is_authenticated=True,
        auth_method="signed_bearer_token",
        issued_at=verified.get("iat", 0),
        expires_at=verified.get("exp", 0)
    )


def get_optional_authenticated_user(
    authorization: Optional[str] = Header(None, description="Bearer session token")
) -> Optional[AuthenticatedUser]:
    """
    Optional authentication for endpoints that support both public metrics and user-filtered views.
    """
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
        verified = verify_session_token(raw_token)
        if verified:
            return AuthenticatedUser(
                user_id=verified["uid"],
                is_authenticated=True,
                auth_method="signed_bearer_token",
                issued_at=verified.get("iat", 0),
                expires_at=verified.get("exp", 0)
            )
    return None


def assert_record_ownership(record_owner_id: str, user: AuthenticatedUser) -> None:
    """
    Enforces server-side authorization check.
    If the requesting identity does not own the record, raises HTTP 403 Forbidden.
    """
    if not record_owner_id:
        return
        
    if user.user_id != record_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization failure: User '{user.user_id}' does not hold access permissions for records belonging to '{record_owner_id}'."
        )
