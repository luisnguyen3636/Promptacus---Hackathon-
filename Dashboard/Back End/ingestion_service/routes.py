import uuid
from datetime import datetime, timezone
from typing import List, Union, Any, Dict

from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError

from .schemas import (
    SessionData,
    SystemConfigData,
    CameraConfigItem,
    LiveMetaData,
    LiveSystemData,
    ThreatOverviewData,
    KPIData,
    InfrastructureData,
    CameraMatrixPayload,
    RecentThreatItem,
    FullCyberguardPayload,
)

ingestion_bp = Blueprint("ingestion", __name__, url_prefix="/api/v1")


def _get_correlation_id() -> str:
    return request.headers.get("X-Correlation-ID") or f"REQ-{uuid.uuid4().hex[:12]}"


def _standard_response(
    success: bool,
    route_name: str,
    correlation_id: str,
    forward_success: bool,
    target_status: int,
    target_response: Any,
    summary: Dict[str, Any],
    http_status: int = 200,
):
    return (
        jsonify({
            "success": success,
            "route": route_name,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "forward_status": "FORWARDED" if forward_success else "FORWARD_FAILED",
            "target_status_code": target_status,
            "target_response": target_response,
            "summary": summary,
        }),
        http_status,
    )


# -------------------------------------------------------------
# R-01: Session
# -------------------------------------------------------------
@ingestion_bp.route("/session", methods=["POST"])
def ingest_session():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = SessionData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/session",
        payload=validated.model_dump(),
        event_type="SESSION_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/session",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={"authenticated": validated.authenticated, "has_user": validated.user is not None},
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-02: System Config
# -------------------------------------------------------------
@ingestion_bp.route("/config/system", methods=["POST"])
def ingest_system_config():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = SystemConfigData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/config/system",
        payload=validated.model_dump(),
        event_type="SYSTEM_CONFIG_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/config/system",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={
            "site_id": validated.site.site_id if validated.site else None,
            "brand": validated.brand.name if validated.brand else None,
        },
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-03: Camera Fleet Registry Config
# -------------------------------------------------------------
@ingestion_bp.route("/config/cameras", methods=["POST"])
def ingest_camera_config():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True)
    if isinstance(data, dict) and "cameras" in data:
        raw_list = data["cameras"]
    elif isinstance(data, list):
        raw_list = data
    else:
        raw_list = [data] if data else []

    try:
        validated = [CameraConfigItem.model_validate(item) for item in raw_list]
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/devices/cameras/config",
        payload=[c.model_dump() for c in validated],
        event_type="CAMERA_REGISTRY_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/config/cameras",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={"total_cameras_configured": len(validated)},
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-04: Live Meta
# -------------------------------------------------------------
@ingestion_bp.route("/live/meta", methods=["POST"])
def ingest_live_meta():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = LiveMetaData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/live/meta",
        payload=validated.model_dump(),
        event_type="LIVE_META_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/meta",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={"sequence": validated.sequence, "stream_mode": validated.stream_mode},
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-05: Live System State
# -------------------------------------------------------------
@ingestion_bp.route("/live/system", methods=["POST"])
def ingest_live_system():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = LiveSystemData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/live/system",
        payload=validated.model_dump(),
        event_type="LIVE_SYSTEM_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/system",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={"state": validated.state, "engine_status": validated.engine_status},
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-06: Live Threat Overview
# -------------------------------------------------------------
@ingestion_bp.route("/live/threat-overview", methods=["POST"])
def ingest_threat_overview():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = ThreatOverviewData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/threat-overview",
        payload=validated.model_dump(),
        event_type="THREAT_OVERVIEW_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/threat-overview",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={"threat_score": validated.threat_score, "open_threats": validated.open_threats.model_dump()},
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-07: Live KPI
# -------------------------------------------------------------
@ingestion_bp.route("/live/kpi", methods=["POST"])
def ingest_live_kpi():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = KPIData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/kpi",
        payload=validated.model_dump(),
        event_type="LIVE_KPI_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/kpi",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={
            "latency_ms": validated.stream_latency_ms,
            "cameras_online": validated.camera_fleet.online,
            "cameras_offline_count": len(validated.camera_fleet.offline),
        },
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-08: Live Infrastructure
# -------------------------------------------------------------
@ingestion_bp.route("/live/infrastructure", methods=["POST"])
def ingest_live_infrastructure():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = InfrastructureData.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/infrastructure",
        payload=validated.model_dump(),
        event_type="INFRASTRUCTURE_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/infrastructure",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={
            "storage_used_tb": validated.nvr_storage.used_tb,
            "poe_load_watts": validated.poe.load_watts,
        },
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-09: Live Camera Matrix
# -------------------------------------------------------------
@ingestion_bp.route("/live/camera-matrix", methods=["POST"])
def ingest_camera_matrix():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = CameraMatrixPayload.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/devices/cameras/matrix",
        payload=validated.model_dump(),
        event_type="CAMERA_MATRIX_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    total_detections = sum(len(t.detections) for t in validated.tiles)
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/camera-matrix",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={"layout": validated.layout, "tiles_count": len(validated.tiles), "total_detections": total_detections},
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-10: Recent Threats & Incidents
# -------------------------------------------------------------
@ingestion_bp.route("/live/incidents", methods=["POST"])
def ingest_recent_threats():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True)
    if isinstance(data, dict) and "recent_threats" in data:
        raw_list = data["recent_threats"]
    elif isinstance(data, list):
        raw_list = data
    else:
        raw_list = [data] if data else []

    try:
        validated = [RecentThreatItem.model_validate(item) for item in raw_list]
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/incidents/recent",
        payload=[item.model_dump() for item in validated],
        event_type="INCIDENTS_RECENT_UPDATE",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502
    return _standard_response(
        success=f_ok,
        route_name="/api/v1/live/incidents",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={
            "incidents_count": len(validated),
            "incident_ids": [item.incident_id for item in validated],
        },
        http_status=status_code,
    )


# -------------------------------------------------------------
# R-11: Master Ingestion Orchestrator (Full Payload)
# -------------------------------------------------------------
@ingestion_bp.route("/ingest/full", methods=["POST"])
def ingest_full_payload():
    correlation_id = _get_correlation_id()
    data = request.get_json(silent=True) or {}
    try:
        validated = FullCyberguardPayload.model_validate(data)
    except ValidationError as e:
        return jsonify({"success": False, "error": "Schema Validation Error", "details": e.errors()}), 422

    forwarder = current_app.extensions["forwarder_service"]
    # Forward full sync to target server
    f_ok, f_code, f_resp = forwarder.forward(
        endpoint="/api/soc/full-sync",
        payload=validated.model_dump(),
        event_type="FULL_PAYLOAD_SYNC",
        correlation_id=correlation_id,
    )
    status_code = 200 if f_ok else 502

    return _standard_response(
        success=f_ok,
        route_name="/api/v1/ingest/full",
        correlation_id=correlation_id,
        forward_success=f_ok,
        target_status=f_code,
        target_response=f_resp,
        summary={
            "schema_version": validated.schema_version,
            "has_session": validated.session is not None,
            "has_config": validated.config is not None,
            "has_live": validated.live is not None,
        },
        http_status=status_code,
    )


# -------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------
@ingestion_bp.route("/health", methods=["GET"])
def health_check():
    forwarder = current_app.extensions.get("forwarder_service")
    dlq_count = forwarder.dlq_manager.get_failed_count() if forwarder else 0
    return jsonify({
        "status": "HEALTHY",
        "service": "CyberGuard Ingestion Gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dlq_pending_records": dlq_count,
        "target_server": forwarder.config.TARGET_SERVER_BASE_URL if forwarder else None,
    }), 200
