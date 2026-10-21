"""
Health Check Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


class HealthCheckResponse(BaseModel):
    status: str = Field(default="healthy", description="Status indicator")
    service: str = Field(default="PathoGuard-Backend", description="Service name")
    version: str = Field(default="1.0.0", description="API version")
    timestamp: str = Field(..., description="ISO 8601 server timestamp")
    environment: Optional[str] = Field(default="development", description="Runtime environment")
