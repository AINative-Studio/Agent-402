"""
Observability schemas for agent decision logging, anomaly detection,
spend drift monitoring, and vendor concentration risk.

Built by AINative Dev Team
Refs #163, #164, #165, #166
"""
from __future__ import annotations

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class DecisionLog(BaseModel):
    """Structured log entry for an agent decision."""

    log_id: str
    agent_id: str
    decision_type: str
    context: Dict[str, Any] = Field(default_factory=dict)
    outcome: str
    confidence: float
    reasoning: str
    timestamp: str
    run_id: Optional[str] = None


class AnomalyReport(BaseModel):
    """Summary of anomaly detection results for an agent."""

    agent_id: str
    total_anomalies: int
    anomaly_rate: float
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)


class DriftAlert(BaseModel):
    """Spend drift alert for a single agent."""

    agent_id: str
    drift_pct: float
    baseline_rate: float
    current_rate: float


class VendorConcentration(BaseModel):
    """Vendor concentration risk analysis result."""

    agent_id: str
    hhi: float
    risk_level: str
    vendors: List[Dict[str, Any]] = Field(default_factory=list)
    total_spend: float
