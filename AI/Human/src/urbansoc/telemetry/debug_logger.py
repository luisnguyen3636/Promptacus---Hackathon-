"""Unified Debug & Audit Logger for Urban Safety AI-SOC Ecosystem.

Provides standardized, high-performance debug logging functions across Python modules,
including MMAction2 action detection, mandatory NVIDIA VLM reasoning, blind-spot
tracking, and HITL operator decisions.
"""

from datetime import datetime, timezone
import json
import logging
import os
import sys
import threading
from typing import Any, Dict, Optional

# ANSI Color codes for readable console debugging
COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[36m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_MAGENTA = "\033[35m"
COLOR_BLUE = "\033[34m"
COLOR_BOLD = "\033[1m"


class UnifiedSOCDebugLogger:
    """Thread-safe multi-sink debug logger for AI-SOC runtime."""

    _instance: Optional["UnifiedSOCDebugLogger"] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "UnifiedSOCDebugLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, log_dir: str = "output/logs") -> None:
        if getattr(self, "_initialized", False):
            return

        self.log_dir = os.path.abspath(log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

        self.debug_log_path = os.path.join(self.log_dir, "soc_debug.log")
        self.mmaction_log_path = os.path.join(self.log_dir, "mmaction2_detection.log")
        self.vlm_log_path = os.path.join(self.log_dir, "nvidia_vlm_mandatory.log")
        self.blind_spot_log_path = os.path.join(self.log_dir, "blind_spot_reasoning.log")

        self.io_lock = threading.Lock()
        self.enabled = True
        self.console_output = True
        self._initialized = True

    def _format_time(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _write_to_file(self, filepath: str, line: str) -> None:
        with self.io_lock:
            try:
                with open(filepath, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as e:
                sys.stderr.write(f"[DEBUG_LOGGER_ERROR] Failed writing to {filepath}: {e}\n")

    def debug(
        self,
        module: str,
        message: str,
        camera_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """General debug log entry."""
        self.log(module=module, message=message, level="DEBUG", camera_id=camera_id, extra=extra)

    def info(
        self,
        module: str,
        message: str,
        camera_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Information level log entry."""
        self.log(module=module, message=message, level="INFO", camera_id=camera_id, extra=extra)

    def warn(
        self,
        module: str,
        message: str,
        camera_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Warning level log entry."""
        self.log(module=module, message=message, level="WARN", camera_id=camera_id, extra=extra)

    def error(
        self,
        module: str,
        message: str,
        camera_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Error level log entry."""
        self.log(module=module, message=message, level="ERROR", camera_id=camera_id, extra=extra)

    def log(
        self,
        module: str,
        message: str,
        level: str = "DEBUG",
        camera_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Core structured logging method."""
        if not self.enabled:
            return

        ts = self._format_time()
        cam_tag = f"[{camera_id}]" if camera_id else "[SYSTEM]"
        extra_str = f" | {json.dumps(extra, ensure_ascii=False)}" if extra else ""
        log_line = f"[{ts}] [{level.upper():5s}] [{module}] {cam_tag} {message}{extra_str}"

        # Write to general debug log file
        self._write_to_file(self.debug_log_path, log_line)

        # Optional console output
        if self.console_output:
            lvl_color = {
                "DEBUG": COLOR_CYAN,
                "INFO": COLOR_GREEN,
                "WARN": COLOR_YELLOW,
                "ERROR": COLOR_RED,
                "CRITICAL": COLOR_MAGENTA,
            }.get(level.upper(), COLOR_RESET)

            print(
                f"{COLOR_YELLOW}[{ts}]{COLOR_RESET} {lvl_color}[{level.upper():5s}]{COLOR_RESET} "
                f"{COLOR_BLUE}[{module}]{COLOR_RESET} {COLOR_MAGENTA}{cam_tag}{COLOR_RESET} {message}"
            )

    def log_pipeline_step(
        self,
        camera_id: str,
        frame_idx: int,
        step_name: str,
        latency_ms: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track frame pipeline progress and latency profiling."""
        msg = f"Frame #{frame_idx} Step: {step_name} (latency: {latency_ms:.2f}ms)"
        self.log(module="AI_PIPELINE", message=msg, level="DEBUG", camera_id=camera_id, extra=details)

    def log_mmaction_event(
        self,
        camera_id: str,
        action_name: str,
        confidence: float,
        bbox: Optional[Any] = None,
        track_id: Optional[str] = None,
        is_criminal: bool = False,
    ) -> None:
        """Dedicated log for MMAction2 spatio-temporal recognition."""
        ts = self._format_time()
        level = "WARN" if is_criminal else "INFO"
        bbox_str = f"bbox={bbox}" if bbox else "bbox=N/A"
        track_str = f"track={track_id}" if track_id else "track=auto"
        msg = (
            f"MMAction2 Action Detected: {action_name} (conf={confidence:.3f}, "
            f"criminal={is_criminal}, {track_str}, {bbox_str})"
        )
        self.log(module="MMACTION2", message=msg, level=level, camera_id=camera_id)

        file_line = f"[{ts}] [{level}] [{camera_id}] ACTION={action_name} CONF={confidence:.3f} CRIMINAL={is_criminal} {track_str} {bbox_str}"
        self._write_to_file(self.mmaction_log_path, file_line)

    def log_vlm_reasoning(
        self,
        camera_id: str,
        verified: bool,
        threat_level: str,
        reasoning_summary: str,
        benign_prob: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Dedicated log for mandatory NVIDIA VLM verification layer."""
        ts = self._format_time()
        level = "WARN" if threat_level.upper() in ("HIGH", "CRITICAL") else "INFO"
        msg = (
            f"Mandatory NVIDIA VLM: verified={verified}, threat={threat_level}, "
            f"benign_prob={benign_prob:.2f} | Reasoning: {reasoning_summary}"
        )
        self.log(module="NVIDIA_VLM", message=msg, level=level, camera_id=camera_id, extra=details)

        file_line = (
            f"[{ts}] [{level}] [{camera_id}] VERIFIED={verified} THREAT={threat_level} "
            f"BENIGN_PROB={benign_prob:.2f} | {reasoning_summary}"
        )
        self._write_to_file(self.vlm_log_path, file_line)

    def log_blind_spot_hop(
        self,
        source_cam: str,
        dest_cam: str,
        blind_spot_zone: str,
        eta_sec: float,
        reid_similarity: Optional[float] = None,
        status: str = "PREDICTED",
    ) -> None:
        """Dedicated log for multi-camera blind spot reasoning and handover."""
        ts = self._format_time()
        reid_str = f"reid_sim={reid_similarity:.3f}" if reid_similarity is not None else "reid_sim=N/A"
        msg = (
            f"Blind-Spot Trajectory: {source_cam} -> [{blind_spot_zone}] -> {dest_cam} | "
            f"Status={status}, ETA={eta_sec:.1f}s, {reid_str}"
        )
        self.log(module="BLIND_SPOT", message=msg, level="INFO", camera_id=source_cam)

        file_line = f"[{ts}] [BLIND_SPOT] {source_cam} -> [{blind_spot_zone}] -> {dest_cam} STATUS={status} ETA={eta_sec:.1f}s {reid_str}"
        self._write_to_file(self.blind_spot_log_path, file_line)


# Global singleton debug logger instance
debug_logger = UnifiedSOCDebugLogger()

# Convenience functional shortcuts
def debug_log(module: str, message: str, camera_id: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    debug_logger.debug(module, message, camera_id=camera_id, extra=extra)

def log_pipeline_step(camera_id: str, frame_idx: int, step_name: str, latency_ms: float = 0.0, details: Optional[Dict[str, Any]] = None) -> None:
    debug_logger.log_pipeline_step(camera_id, frame_idx, step_name, latency_ms=latency_ms, details=details)

def log_mmaction_event(camera_id: str, action_name: str, confidence: float, bbox: Optional[Any] = None, track_id: Optional[str] = None, is_criminal: bool = False) -> None:
    debug_logger.log_mmaction_event(camera_id, action_name, confidence, bbox=bbox, track_id=track_id, is_criminal=is_criminal)

def log_vlm_reasoning(camera_id: str, verified: bool, threat_level: str, reasoning_summary: str, benign_prob: float = 0.0, details: Optional[Dict[str, Any]] = None) -> None:
    debug_logger.log_vlm_reasoning(camera_id, verified, threat_level, reasoning_summary, benign_prob=benign_prob, details=details)

def log_blind_spot_hop(source_cam: str, dest_cam: str, blind_spot_zone: str, eta_sec: float, reid_similarity: Optional[float] = None, status: str = "PREDICTED") -> None:
    debug_logger.log_blind_spot_hop(source_cam, dest_cam, blind_spot_zone, eta_sec, reid_similarity=reid_similarity, status=status)
