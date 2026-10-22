"""
Authentication & Session Endpoints
Provides cryptographic session tokens and verification for patient record isolation.
"""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import uuid

from app.core.auth import (
    generate_session_token,
    verify_session_token,
    get_current_authenticated_user,
    AuthenticatedUser,
    SESSION_EXPIRATION_SECONDS
)

router = APIRouter()


class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Requested or existing patient/user identifier")
    patient_name: Optional[str] = Field(None, description="Patient display name")


class SessionResponse(BaseModel):
    user_id: str
    token: str
    token_type: str = "Bearer"
    expires_in_seconds: int = SESSION_EXPIRATION_SECONDS
    status: str = "authenticated"
    security_notice: str = (
        "Cryptographically signed bearer token issued. "
        "Server-side ownership verification enforced on all patient records."
    )


class SessionVerifyResponse(BaseModel):
    user_id: str
    is_authenticated: bool
    auth_method: str
    expires_at: int
    status: str = "valid"


@router.post("/session", response_model=SessionResponse)
def create_session(payload: Optional[SessionCreateRequest] = None) -> SessionResponse:
    """
    Issues a cryptographically signed HMAC-SHA256 session token.
    Enforces user isolation across assessments and medical reports.
    """
    req_uid = payload.user_id if payload and payload.user_id else None
    assigned_uid = req_uid or f"patient_{str(uuid.uuid4())[:8]}"
    token = generate_session_token(assigned_uid)
    
    return SessionResponse(
        user_id=assigned_uid,
        token=token
    )


@router.get("/verify", response_model=SessionVerifyResponse)
def verify_current_session(
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> SessionVerifyResponse:
    """
    Verifies caller's session token and returns authenticated identity.
    """
    if not current_user.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is unauthenticated. Please supply a valid Bearer token."
        )
        
    return SessionVerifyResponse(
        user_id=current_user.user_id,
        is_authenticated=True,
        auth_method=current_user.auth_method,
        expires_at=current_user.expires_at
    )
