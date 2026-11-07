import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional
import requests

from .config import IngestionConfig

logger = logging.getLogger("cyberguard.forwarder")


class DLQManager:
    """Dead-Letter Queue (DLQ) Manager for persistent storage of failed forwarding payloads."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)
        self.file_path = os.path.join(self.storage_path, "failed_packets.jsonl")

    def enqueue(self, route: str, payload: Any, error_reason: str, correlation_id: str) -> str:
        record = {
            "correlation_id": correlation_id,
            "route": route,
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "error_reason": error_reason,
            "payload": payload,
        }
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logger.warning(
                f"[DLQ] Record saved to DLQ: id={correlation_id}, route={route}, reason={error_reason}"
            )
            return self.file_path
        except Exception as e:
            logger.error(f"[DLQ FATAL] Failed to write record to DLQ: {str(e)}")
            return ""

    def get_failed_count(self) -> int:
        if not os.path.exists(self.file_path):
            return 0
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0


class ForwarderService:
    """HTTP Forwarder Service with Timeout, Exponential Backoff, and SOC-Grade HITL Enforcement."""

    def __init__(self, config: IngestionConfig, dlq_manager: Optional[DLQManager] = None):
        self.config = config
        self.dlq_manager = dlq_manager or DLQManager(config.DLQ_STORAGE_PATH)
        self.session = requests.Session()

    def enforce_hitl_check(self, payload: Any, event_type: str) -> Any:
        """
        Rule [CD-04] Compliance: Ensures that events with HIGH or CRITICAL severity
        cannot bypass Human Operator verification.
        """
        # If payload is a list of incidents
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    sev = str(item.get("severity", "")).upper()
                    if sev in ("HIGH", "CRITICAL"):
                        if item.get("status") != "OPERATOR_CONFIRMED" or not item.get("assignee"):
                            item["requires_operator_verification"] = True
                            item["dispatch_restricted"] = True
        elif isinstance(payload, dict):
            sev = str(payload.get("severity", "")).upper()
            if sev in ("HIGH", "CRITICAL"):
                if payload.get("status") != "OPERATOR_CONFIRMED":
                    payload["requires_operator_verification"] = True
                    payload["dispatch_restricted"] = True

        return payload

    def forward(
        self,
        endpoint: str,
        payload: Any,
        event_type: str,
        correlation_id: str
    ) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Forward payload to the Target Server with retry and fallback to DLQ.
        Returns: (success: bool, status_code: int, response_data: dict)
        """
        # Apply SOC HITL Safety Filter
        secured_payload = self.enforce_hitl_check(payload, event_type)

        target_base = self.config.TARGET_SERVER_BASE_URL.rstrip("/")
        normalized_endpoint = "/" + endpoint.lstrip("/")
        target_url = f"{target_base}{normalized_endpoint}"

        headers = {
            "Content-Type": "application/json",
            "X-Cyberguard-Event-Type": event_type,
            "X-Correlation-ID": correlation_id,
            "X-API-Key": self.config.TARGET_SERVER_API_KEY,
            "X-Gateway-Timestamp": datetime.now(timezone.utc).isoformat(),
        }

        timeout_sec = max(0.5, self.config.TARGET_SERVER_TIMEOUT_MS / 1000.0)
        max_retries = max(1, self.config.TARGET_SERVER_MAX_RETRIES)

        last_error = ""
        last_status = 502

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"[FORWARD] Attempt {attempt}/{max_retries} -> {target_url} [corr_id={correlation_id}]"
                )
                resp = self.session.post(
                    target_url,
                    json=secured_payload,
                    headers=headers,
                    timeout=timeout_sec
                )
                last_status = resp.status_code

                if resp.status_code in (200, 201, 202, 204):
                    logger.info(
                        f"[FORWARD SUCCESS] {target_url} returned {resp.status_code} [corr_id={correlation_id}]"
                    )
                    try:
                        resp_data = resp.json()
                    except Exception:
                        resp_data = {"raw_text": resp.text}
                    return True, resp.status_code, resp_data

                # Server error: 5xx, or 429: can retry
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(
                    f"[FORWARD RETRYABLE] {target_url} failed with {last_error} (attempt {attempt})"
                )

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as req_err:
                last_error = f"{type(req_err).__name__}: {str(req_err)}"
                logger.warning(
                    f"[FORWARD NETWORK ERROR] {target_url} failed: {last_error} (attempt {attempt})"
                )
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(
                    f"[FORWARD UNEXPECTED] {target_url} error: {last_error}"
                )
                break

            # Backoff before next attempt
            if attempt < max_retries:
                backoff = 0.1 * (2 ** (attempt - 1))
                time.sleep(backoff)

        # Retries exhausted -> enqueue in DLQ
        if self.config.ENABLE_DEAD_LETTER_QUEUE:
            self.dlq_manager.enqueue(
                route=endpoint,
                payload=secured_payload,
                error_reason=last_error,
                correlation_id=correlation_id
            )

        return False, last_status, {
            "error": "Failed to forward payload to target server after retries",
            "last_error": last_error,
            "target_url": target_url,
            "buffered_to_dlq": self.config.ENABLE_DEAD_LETTER_QUEUE
        }
