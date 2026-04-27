import os
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/config", tags=["config"])

# In-memory config store (persists for the process lifetime)
_thresholds: dict = {}


def _defaults() -> dict:
    return {
        "open_rate_warn": float(os.getenv("OPEN_RATE_WARN", "0.25")),
        "open_rate_critical": float(os.getenv("OPEN_RATE_CRITICAL", "0.15")),
        "reply_rate_warn": float(os.getenv("REPLY_RATE_WARN", "0.03")),
        "reply_rate_critical": float(os.getenv("REPLY_RATE_CRITICAL", "0.01")),
        "bounce_rate_warn": float(os.getenv("BOUNCE_RATE_WARN", "0.03")),
        "bounce_rate_critical": float(os.getenv("BOUNCE_RATE_CRITICAL", "0.05")),
        "cache_ttl_minutes": int(os.getenv("CACHE_TTL_MINUTES", "30")),
    }


def get_thresholds() -> dict:
    if not _thresholds:
        _thresholds.update(_defaults())
    return dict(_thresholds)


class ThresholdUpdate(BaseModel):
    open_rate_warn: Optional[float] = None
    open_rate_critical: Optional[float] = None
    reply_rate_warn: Optional[float] = None
    reply_rate_critical: Optional[float] = None
    bounce_rate_warn: Optional[float] = None
    bounce_rate_critical: Optional[float] = None
    cache_ttl_minutes: Optional[int] = None


@router.get("/thresholds")
def read_thresholds():
    return get_thresholds()


@router.post("/thresholds")
def update_thresholds(body: ThresholdUpdate):
    current = get_thresholds()
    updates = body.model_dump(exclude_none=True)
    current.update(updates)
    _thresholds.clear()
    _thresholds.update(current)
    return {"updated": True}
