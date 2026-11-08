#!/usr/bin/env python3
"""
Dedicated AI Alert Server for Urban Safety AI-SOC.
Receives suspicious action reports from detector agents, executes AI multimodal
evaluation, intent prediction ("dự kiến"), timestamping ("đánh dấu thời gian"),
cryptographic hashing ("mã hash"), and returns 100% structured JSON Alert objects.
"""

import os
import sys
import json
import time
import argparse
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Dict, Any, List
from collections import deque
from datetime import datetime

# Dependency check & import
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from alert_models import SuspiciousActionRequest, AlertRecord
from ai_service import AIService, load_env_file
from rate_limiter import AIRateLimitExceededError, SlidingWindowRateLimiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("urbansoc.server")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server allowing concurrent request handling."""
    daemon_threads = True
    allow_reuse_address = True


class AlertRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler servicing Alert ingestion, verification, and JSON responses."""

    server_instance: "AlertServer"

    @property
    def alert_server(self) -> "AlertServer":
        return getattr(self.server, "alert_server", None)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests: status, recent alerts, evidence images."""
        clean_path = self.path.split("?")[0].rstrip("/")

        # 1. Health check & Root info
        if clean_path in ("", "/", "/health", "/api/v1/health"):
            self._handle_health_check()
            return

        # 2. List recent alerts
        if clean_path in ("/api/incident", "/api/incidents", "/api/v1/incident", "/api/v1/incidents", "/api/v1/alerts", "/api/alerts"):
            self._handle_get_alerts()
            return

        # 3. Serve evidence snapshot JPEG
        if clean_path.startswith("/api/v1/evidence/"):
            self._handle_serve_evidence(clean_path)
            return

        self._send_json_response(404, {"status": "error", "message": f"Endpoint '{clean_path}' not found."})

    def do_POST(self) -> None:
        """Handle POST requests: ingest suspicious action from detector agent."""
        clean_path = self.path.split("?")[0].rstrip("/")

        # Incident ingestion endpoints (supports /api/incident, /api/v1/alerts, etc.)
        if clean_path in (
            "/api/incident",
            "/api/incidents",
            "/api/v1/incident",
            "/api/v1/incidents",
            "/api/v1/alerts",
            "/api/alerts",
            "/api/v1/analyze",
        ):
            self._handle_post_alert()
            return

        self._send_json_response(404, {"status": "error", "message": f"Endpoint '{clean_path}' not found."})

    def _handle_health_check(self) -> None:
        """Returns server health, AI configuration, and uptime."""
        ai_svc = self.alert_server.ai_service
        info = {
            "status": "online",
            "service": "Urban Safety AI-SOC Alert Server",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "ai_configured": ai_svc.is_configured(),
            "ai_model": ai_svc.model,
            "ai_endpoint": ai_svc.base_url,
            "total_alerts_received": len(self.alert_server.recent_alerts),
            "endpoints": {
                "submit_incident": "POST /api/incident",
                "submit_alert": "POST /api/v1/alerts",
                "list_alerts": "GET /api/incident",
                "health": "GET /api/v1/health",
                "evidence": "GET /api/v1/evidence/<filename>"
            }
        }
        self._send_json_response(200, info)

    def _handle_get_alerts(self) -> None:
        """Returns JSON array of stored recent alerts."""
        alerts = []
        for a in reversed(self.alert_server.recent_alerts):
            if hasattr(a, "to_dict"):
                alerts.append(a.to_dict())
            elif isinstance(a, dict):
                alerts.append(a)
        self._send_json_response(200, {
            "status": "success",
            "count": len(alerts),
            "alerts": alerts
        })

    def _handle_serve_evidence(self, clean_path: str) -> None:
        """Serves evidence snapshot JPEG."""
        filename = clean_path.split("/")[-1]
        filepath = os.path.join(self.alert_server.ai_service.evidence_dir, filename)

        if not os.path.exists(filepath):
            self._send_json_response(404, {"status": "error", "message": f"Evidence image '{filename}' not found."})
            return

        try:
            with open(filepath, "rb") as f:
                img_data = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(img_data)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(img_data)
        except Exception as e:
            self._send_json_response(500, {"status": "error", "message": f"Could not read image: {e}"})

    def _handle_post_alert(self) -> None:
        """
        Receives incident payload at endpoint:
        - If payload is an AI-generated AlertRecord (has alert_id and hash), verifies and records incident.
        - If payload is raw camera detection (SuspiciousActionRequest), invokes AI Service (Rate limited: 40 req/min).
        """
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            self._send_json_response(400, {"status": "error", "message": "Missing request body or Content-Length."})
            return

        raw_body = self.rfile.read(content_length)

        try:
            data = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_json_response(400, {"status": "error", "message": f"Invalid JSON payload: {e}"})
            return

        # Case 1: Payload is already an AI-generated AlertRecord
        if isinstance(data, dict) and "alert_id" in data and "hash" in data:
            self.alert_server.record_alert_dict(data)
            self._send_json_response(200, {
                "status": "success",
                "message": "Incident successfully received and recorded at endpoint",
                "incident": data
            })
            return

        # Case 2: Raw camera detection -> Process with AI Service (Rate-limited to 40 req/min)
        request = SuspiciousActionRequest.from_dict(data)

        try:
            alert_record: AlertRecord = self.alert_server.ai_service.process_suspicious_action(request)

            # Store in server memory and append to jsonl
            self.alert_server.record_alert(alert_record)

            # Return 100% JSON response
            self._send_json_response(200, alert_record.to_dict())

        except AIRateLimitExceededError as rle:
            self._send_json_response(429, {
                "status": "error",
                "code": 429,
                "message": str(rle),
                "retry_after_seconds": round(rle.retry_after, 2)
            })
        except Exception as e:
            logger.exception("Error processing suspicious action alert: %s", e)
            self._send_json_response(500, {
                "status": "error",
                "message": f"Internal server error processing alert: {e}"
            })

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Camera-ID")

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Sends standardized JSON response."""
        response_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(response_bytes)


class AlertServer:
    """
    Core Alert Server orchestrator managing HTTP server lifecycle,
    AI evaluation, and alert persistence.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        output_dir: str = "output",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        load_env_file()

        self.host = host
        self.port = port
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.alerts_log_file = os.path.join(self.output_dir, "alerts.jsonl")
        self.recent_alerts: deque = deque(maxlen=100)

        # Initialize AI Service
        self.ai_service = AIService(
            api_key=api_key,
            base_url=base_url,
            model=model,
            output_dir=self.output_dir
        )

        self.http_server: Optional[ThreadedHTTPServer] = None
        self._is_running = False

    def record_alert(self, alert: AlertRecord) -> None:
        """Stores alert in memory and persists to alerts.jsonl."""
        self.recent_alerts.append(alert)
        try:
            with open(self.alerts_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")
            logger.info("🚨 [ALERT DISPATCHED] ID: %s | Action: %s | Severity: %s | Hash: %s... | Score: %.2f",
                        alert.alert_id, alert.action_type, alert.severity, alert.hash[:12], alert.threat_score)
        except Exception as e:
            logger.error("Could not append alert to log: %s", e)

    def record_alert_dict(self, alert_dict: dict) -> None:
        """Stores received AI-generated alert dict in memory and persists to alerts.jsonl."""
        self.recent_alerts.append(alert_dict)
        try:
            with open(self.alerts_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_dict, ensure_ascii=False) + "\n")
            logger.info("🚨 [INCIDENT RECORDED AT ENDPOINT] ID: %s | Action: %s | Severity: %s | Hash: %s...",
                        alert_dict.get("alert_id"), alert_dict.get("action_type"), alert_dict.get("severity"), str(alert_dict.get("hash", ""))[:12])
        except Exception as e:
            logger.error("Could not append alert to log: %s", e)

    def start(self, blocking: bool = True) -> None:
        """Starts the HTTP server."""
        server_address = (self.host, self.port)
        self.http_server = ThreadedHTTPServer(server_address, AlertRequestHandler)
        self.http_server.alert_server = self  # Attach reference

        self._is_running = True
        logger.info("=================================================================")
        logger.info(" URBAN SAFETY AI-SOC: DEDICATED AI ALERT SERVER ONLINE           ")
        logger.info(" Listening on http://%s:%d", self.host, self.port)
        logger.info(" AI Model     : %s", self.ai_service.model)
        logger.info(" AI Endpoint  : %s", self.ai_service.base_url)
        logger.info(" AI Key Active: %s", self.ai_service.is_configured())
        logger.info(" Alerts Log   : %s", self.alerts_log_file)
        logger.info("=================================================================")

        if blocking:
            try:
                self.http_server.serve_forever()
            except KeyboardInterrupt:
                logger.info("Server shutting down on user interrupt...")
            finally:
                self.stop()

    def stop(self) -> None:
        """Stops the server gracefully."""
        self._is_running = False
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
            logger.info("Alert Server stopped cleanly.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Urban Safety AI-SOC Dedicated AI Alert Server")
    parser.add_argument("port", type=int, nargs="?", default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory for logs and evidence")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = AlertServer(
        host=args.host,
        port=args.port,
        output_dir=args.output_dir
    )
    server.start(blocking=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
