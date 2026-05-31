"""GenTwin alert contract — canonical payload for Telegram and downstream systems."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class FaultCode(str, Enum):
    TWF = "TWF"
    HDF = "HDF"
    PWF = "PWF"
    OSF = "OSF"
    RNF = "RNF"
    NORMAL = "NORMAL"


class SafetyPriority(int, Enum):
    ADVISORY = 1
    WARNING = 2
    CRITICAL_SHUTDOWN = 3


class SensorSnapshot(BaseModel):
    PS1: float = Field(..., description="Hydraulic pressure (bar)")
    PS2: float = Field(..., description="Pneumatic pressure (bar)")
    TS1: float = Field(..., description="Air temperature (K)")
    TS2: float = Field(..., description="Process temperature (K)")
    Torque: float = Field(..., description="Torque (Nm)")
    Speed: float = Field(..., description="Rotational speed (rpm)")
    Wear: float = Field(..., description="Tool wear (min)")


class RecoveryArtifact(BaseModel):
    faultCode: str
    hazop_status: str
    target_pressure_ps1: float
    action: str
    confidence: float
    source_doc: str
    safetyPriority: int
    clearing_duration_s: int = 30


class SopStep(BaseModel):
    step: int
    instruction: str
    source: Optional[str] = None


class CascadeRisk(BaseModel):
    summary: str
    probability_bearing_to_shaft: Optional[float] = None
    probability_shaft_to_motor: Optional[float] = None
    estimated_downtime_usd: Optional[int] = None


class GenTwinAlert(BaseModel):
    """Full alert contract sent to Telegram and stored in Supabase/n8n later."""

    alert_id: str
    plant_name: str
    timestamp_utc: str
    anomaly_detected: bool
    fault_code: str
    fault_name: str
    root_cause: str
    safety_priority: int
    severity_label: str
    affected_component: str
    sensors: SensorSnapshot
    sensor_analysis: dict[str, str]
    hazop_status: str
    hazop_detail: str
    artifact: Optional[RecoveryArtifact] = None
    sop_steps: list[SopStep] = Field(default_factory=list)
    prevention: list[str] = Field(default_factory=list)
    cascade: Optional[CascadeRisk] = None
    latency_ms: dict[str, float] = Field(default_factory=dict)
    source: str = Field(default="contract", description="contract | gemini | hybrid")
    narrative: Optional[str] = Field(default=None, description="Optional Gemini-enriched summary")

    def to_telegram_dict(self) -> dict[str, Any]:
        return self.model_dump()
