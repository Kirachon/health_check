"""Schemas for alert webhook payloads."""
from typing import Dict, List, Optional

from pydantic import BaseModel


class GrafanaAlert(BaseModel):
    status: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None
    valueString: Optional[str] = None

    class Config:
        extra = "allow"


class GrafanaWebhookPayload(BaseModel):
    receiver: Optional[str] = None
    status: Optional[str] = None
    alerts: List[GrafanaAlert] = []

    class Config:
        extra = "allow"
