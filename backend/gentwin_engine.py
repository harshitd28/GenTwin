"""GenTwin pipeline engine — contract backend (no LLM required)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alert_contract import (
    CascadeRisk,
    FaultCode,
    GenTwinAlert,
    RecoveryArtifact,
    SensorSnapshot,
    SopStep,
)

SENSORS = [
    {"id": "PS1", "norm": (155, 160), "unit": "bar"},
    {"id": "PS2", "norm": (100, 105), "unit": "bar"},
    {"id": "TS1", "norm": (298, 302), "unit": "K"},
    {"id": "TS2", "norm": (305, 310), "unit": "K"},
    {"id": "Torque", "norm": (35, 55), "unit": "Nm"},
    {"id": "Speed", "norm": (1400, 1600), "unit": "rpm"},
    {"id": "Wear", "norm": (0, 180), "unit": "min"},
]

LATENCY = {
    "L1_ingestion_ms": 3.1,
    "L2_stage1_rf_ms": 9.8,
    "L2_stage2_xgb_ms": 15.2,
    "L3_chromadb_ms": 312.0,
    "L3_orchestration_ms": 189.0,
    "L3_gemini_ms": 741.0,
    "L4_hazop_ms": 38.0,
    "total_ms": 1119.0,
}

FAKE_PRESETS: dict[str, dict[str, float]] = {
    "normal": {
        "PS1": 157.5,
        "PS2": 102,
        "TS1": 300,
        "TS2": 307,
        "Torque": 42,
        "Speed": 1500,
        "Wear": 120,
    },
    "hdf": {
        "PS1": 158,
        "PS2": 103,
        "TS1": 298,
        "TS2": 309,
        "Torque": 45,
        "Speed": 1480,
        "Wear": 130,
    },
    "pwf": {
        "PS1": 128,
        "PS2": 98,
        "TS1": 301,
        "TS2": 308,
        "Torque": 38,
        "Speed": 1200,
        "Wear": 140,
    },
    "osf": {
        "PS1": 156,
        "PS2": 101,
        "TS1": 300,
        "TS2": 307,
        "Torque": 78,
        "Speed": 1350,
        "Wear": 150,
    },
    "twf": {
        "PS1": 157,
        "PS2": 102,
        "TS1": 300,
        "TS2": 307,
        "Torque": 40,
        "Speed": 1500,
        "Wear": 215,
    },
    "hazop_violation": {
        "PS1": 175,
        "PS2": 102,
        "TS1": 300,
        "TS2": 307,
        "Torque": 42,
        "Speed": 1500,
        "Wear": 120,
    },
}

FAULT_META = {
    "TWF": {
        "name": "Tool Wear Failure",
        "root": "Cumulative tool wear crossed 200–240 min OEM threshold.",
        "component": "Cutting tool / wear counter W-04",
        "prio": 2,
        "action": "tool_change_procedure",
    },
    "HDF": {
        "name": "Heat Dissipation Failure",
        "root": "ΔT between TS1 and TS2 exceeded 8.6K — thermal runaway signature.",
        "component": "Heat exchanger HX-3 / kiln feed",
        "prio": 2,
        "action": "thermal_runaway_mitigation",
    },
    "PWF": {
        "name": "Power Failure",
        "root": "Torque/speed mismatch — insufficient power P = τω at current operating point.",
        "component": "Pneumatic valve V-12 / PS1 circuit",
        "prio": 2,
        "action": "valve_switching_lag_clear",
    },
    "OSF": {
        "name": "Overstrain Failure",
        "root": "Torque > 72 Nm at low RPM — drive shaft overload signature.",
        "component": "Drive shaft DS-2 / Bearing B2",
        "prio": 2,
        "action": "torque_limit_reduction",
    },
    "RNF": {
        "name": "Random Failure",
        "root": "Stochastic anomaly not fully explained by orthogonal sensor signatures.",
        "component": "General line",
        "prio": 1,
        "action": "standard_inspection",
    },
}

SOP_BY_FAULT: dict[str, list[str]] = {
    "PWF": [
        "Isolate pneumatic supply valve V-12 immediately.",
        "Verify PS1 stabilises above 140 bar within 30 seconds.",
        "Execute valve_switching_lag_clear per FLSmidth Ch.4 §3.2.",
        "Monitor torque/speed ratio for 60s before resuming feed.",
    ],
    "HDF": [
        "Reduce kiln feed rate by 15%.",
        "Activate auxiliary cooling circuit on HX-3.",
        "Confirm ΔT drops below 8.6K within 120 seconds.",
        "Log thermal event to CMMS; inspect heat exchanger if not cleared.",
    ],
    "OSF": [
        "Reduce torque limit to 55 Nm via PLC register T-LIM.",
        "Lower rotational speed to 1300 rpm.",
        "Inspect drive shaft coupling DS-2 before restart.",
        "Schedule bearing B2 vibration analysis.",
    ],
    "TWF": [
        "Stop production cycle safely.",
        "Replace worn tool per OEM interval table.",
        "Reset wear counter in PLC register W-04.",
        "Run 5-minute calibration cycle before full load.",
    ],
    "RNF": [
        "Capture full sensor snapshot to incident log.",
        "Run diagnostic checklist DR-07.",
        "Escalate to maintenance engineering — do not override interlocks.",
    ],
}

PREVENTION_BY_FAULT: dict[str, list[str]] = {
    "PWF": [
        "Schedule quarterly valve V-12 lag tests.",
        "Keep PS1/PS2 within ±5 bar of nominal during load changes.",
    ],
    "HDF": [
        "Monitor ΔT trend; alert at 7.5K advisory threshold.",
        "Maintain HX-3 fouling inspection every 90 days.",
    ],
    "OSF": [
        "Enforce torque ceiling 72 Nm below 1400 rpm in PLC.",
        "Vibration baseline on Bearing B2 weekly.",
    ],
    "TWF": [
        "Replace tool at 180 min wear (before 200 min hard limit).",
    ],
    "RNF": [
        "Increase Stage 1 RF sampling during known noisy shifts.",
    ],
}


def _in_norm(value: float, low: float, high: float) -> bool:
    return low <= value <= high


def stage1_anomaly(s: dict[str, float]) -> bool:
    """Recall-first gate: out-of-band sensors OR known fault signatures."""
    for spec in SENSORS:
        lo, hi = spec["norm"]
        if not _in_norm(s[spec["id"]], lo, hi):
            return True
    d_t = s["TS2"] - s["TS1"]
    if d_t > 8.6 or s["Wear"] >= 200:
        return True
    if s["Torque"] > 72 and s["Speed"] < 1400:
        return True
    if s["Torque"] * s["Speed"] / 9550 < 35 or s["PS1"] < 140:
        return True
    if s["PS1"] > 130:
        return True
    return False


def classify_fault(s: dict[str, float]) -> str:
    d_t = s["TS2"] - s["TS1"]
    if s["Wear"] >= 200:
        return "TWF"
    if d_t > 8.6:
        return "HDF"
    if s["Torque"] > 72 and s["Speed"] < 1400:
        return "OSF"
    power_kw = s["Torque"] * s["Speed"] / 9550
    if power_kw < 35 or s["PS1"] < 140:
        return "PWF"
    return "RNF"


def analyze_sensors(s: dict[str, float]) -> dict[str, str]:
    lines: dict[str, str] = {}
    d_t = s["TS2"] - s["TS1"]
    lines["delta_T"] = f"ΔT = {d_t:.1f}K (HDF threshold > 8.6K)"
    lines["PS1"] = f"PS1 = {s['PS1']:.1f} bar (burst limit 130 bar)"
    lines["Torque_Speed"] = f"Torque {s['Torque']:.0f} Nm @ {s['Speed']:.0f} rpm"
    lines["Wear"] = f"Tool wear {s['Wear']:.0f} min (TWF threshold ≥ 200 min)"
    return lines


def build_artifact(s: dict[str, float], code: str, unsafe: bool) -> RecoveryArtifact:
    meta = FAULT_META[code]
    target = 175.0 if unsafe else min(130.0, s["PS1"])
    return RecoveryArtifact(
        faultCode=code,
        hazop_status="BLOCK" if unsafe else "PASS",
        target_pressure_ps1=target,
        action=meta["action"],
        confidence=0.42 if unsafe else 0.97,
        source_doc="FLSmidth_Ch4.pdf §3.2",
        safetyPriority=meta["prio"],
    )


def run_pipeline(
    telemetry: dict[str, float],
    plant_name: str = "JK Cement — Rotary Kiln Line 2",
) -> GenTwinAlert:
    alert_id = f"GT-{uuid.uuid4().hex[:8].upper()}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    snap = SensorSnapshot(**telemetry)

    if not stage1_anomaly(telemetry):
        return GenTwinAlert(
            alert_id=alert_id,
            plant_name=plant_name,
            timestamp_utc=ts,
            anomaly_detected=False,
            fault_code=FaultCode.NORMAL.value,
            fault_name="Normal Operation",
            root_cause="All sensors within validated operating bands.",
            safety_priority=1,
            severity_label="ADVISORY",
            affected_component="—",
            sensors=snap,
            sensor_analysis=analyze_sensors(telemetry),
            hazop_status="PASS",
            hazop_detail="No anomaly — pipeline bypassed. 82.9% LLM reduction active.",
            latency_ms={"total_ms": 12.0},
            prevention=["Continue standard monitoring."],
        )

    code = classify_fault(telemetry)
    meta = FAULT_META[code]
    unsafe = telemetry["PS1"] > 130
    artifact = build_artifact(telemetry, code, unsafe)
    hazop_detail = (
        f"BLOCKED: target pressure {artifact.target_pressure_ps1:.0f} bar exceeds "
        f"130 bar burst threshold — artifact rejected, loop to L2."
        if unsafe
        else "PASS: all parameters within HAZOP physics envelope (N=100 trials, 0 violations)."
    )
    sop_raw = SOP_BY_FAULT.get(code, SOP_BY_FAULT["RNF"])
    sop = [
        SopStep(step=i + 1, instruction=t, source=artifact.source_doc)
        for i, t in enumerate(sop_raw)
    ]
    cascade = None
    if code in ("PWF", "OSF"):
        cascade = CascadeRisk(
            summary="Monte Carlo cascade forecast (N=1000, 85th percentile)",
            probability_bearing_to_shaft=0.84,
            probability_shaft_to_motor=0.91,
            estimated_downtime_usd=180_000,
        )

    severity = {1: "ADVISORY", 2: "WARNING", 3: "CRITICAL SHUTDOWN"}[meta["prio"]]

    return GenTwinAlert(
        alert_id=alert_id,
        plant_name=plant_name,
        timestamp_utc=ts,
        anomaly_detected=True,
        fault_code=code,
        fault_name=meta["name"],
        root_cause=meta["root"],
        safety_priority=meta["prio"],
        severity_label=severity,
        affected_component=meta["component"],
        sensors=snap,
        sensor_analysis=analyze_sensors(telemetry),
        hazop_status=artifact.hazop_status,
        hazop_detail=hazop_detail,
        artifact=artifact,
        sop_steps=sop,
        prevention=PREVENTION_BY_FAULT.get(code, []),
        cascade=cascade,
        latency_ms=LATENCY.copy(),
        source="contract",
    )
