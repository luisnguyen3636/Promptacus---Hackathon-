"""SOC Top HUD Dashboard and Diagnostic Telemetry Overlay with responsive layout."""

from typing import Tuple

import cv2
import numpy as np

from urbansoc.domain.enums import ThreatLevel
from urbansoc.domain.schemas import SOCFrameAnalysisResult
from urbansoc.render.theme import THREAT_COLORS


def draw_soc_hud_dashboard(
    image: np.ndarray,
    analysis: SOCFrameAnalysisResult,
    fps: float,
) -> np.ndarray:
    """Draw the 44px top SOC status bar containing system brand, audit clock, status badge, and metrics."""
    h, w = image.shape[:2]
    bar_h = min(44, int(h * 0.12))

    # Semi-transparent dark overlay
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, bar_h), (12, 12, 16), -1)
    cv2.addWeighted(overlay, 0.78, image, 0.22, 0, image)

    # Bottom border line
    cv2.line(image, (0, bar_h), (w, bar_h), (55, 55, 65), 1, cv2.LINE_AA)

    # Line 1: Header Brand
    cv2.putText(
        image,
        "URBAN SAFETY SOC | YOLO11-POSE + BYTETRACK + BEHAVIOR ENGINE",
        (12, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    # Line 2: SOC Audit Clock
    cv2.putText(
        image,
        f"TIME: {analysis.timestamp}",
        (12, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )

    # Right Status Badge
    badge_color = THREAT_COLORS[analysis.highest_threat_level]["box"]
    if analysis.highest_threat_level == ThreatLevel.CRITICAL:
        evt_str = analysis.critical_events[0] if analysis.critical_events else "EMERGENCY"
        badge_text = f"[ CRITICAL: {evt_str} ]"
    elif analysis.highest_threat_level == ThreatLevel.HIGH:
        evt_str = analysis.critical_events[0] if analysis.critical_events else "SUSPICIOUS"
        badge_text = f"[ HIGH ALERT: {evt_str} ]"
    elif analysis.highest_threat_level == ThreatLevel.MEDIUM:
        badge_text = f"[ ELEVATED: {analysis.human_count} PERSON(S) MONITORED ]"
    else:
        if analysis.has_human:
            badge_text = f"[ NORMAL: {analysis.human_count} PERSON(S) CLEAR ]"
        else:
            badge_text = "[ CLEAR: NO ACTIVITY ]"

    if len(badge_text) > 48:
        badge_text = badge_text[:45] + "... ]"

    font_scale = 0.38
    (tw, th), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)

    rec_offset = 65 if analysis.is_recording_evidence else 12
    badge_x = max(int(w * 0.40), w - tw - rec_offset)
    cv2.putText(
        image,
        badge_text,
        (badge_x, 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        badge_color,
        1,
        cv2.LINE_AA,
    )

    # Real-time metrics
    metrics_str = f"FPS: {fps:.1f} | INFER: {analysis.inference_time_ms:.0f}ms | BEH: {analysis.behavior_time_ms:.0f}ms"
    cv2.putText(
        image,
        metrics_str,
        (badge_x, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.33,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )

    # Evidence Recording Indicator
    if analysis.is_recording_evidence:
        cv2.circle(image, (w - 20, 24), 6, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.putText(
            image,
            "REC",
            (w - 52, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (0, 0, 255),
            1,
            cv2.LINE_AA,
        )

    return image


def draw_diagnostic_alert_box(
    image: np.ndarray,
    analysis: SOCFrameAnalysisResult,
) -> np.ndarray:
    """Draw the real-time biometric and telemetry diagnostic alert box (toggled with 'd')."""
    h, w = image.shape[:2]
    box_w = min(410, int(w * 0.60))
    box_h = min(165, int(h * 0.40))
    bx1 = 12
    by1 = h - box_h - 12
    bx2 = bx1 + box_w
    by2 = by1 + box_h

    # Semi-transparent dark background
    overlay = image.copy()
    cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (8, 8, 12), -1)
    cv2.addWeighted(overlay, 0.85, image, 0.15, 0, image)

    # Border
    cv2.rectangle(image, (bx1, by1), (bx2, by2), (65, 65, 75), 1, cv2.LINE_AA)

    # Title
    cv2.putText(
        image,
        "[ DIAGNOSTIC TELEMETRY - TOGGLE 'd' ]",
        (bx1 + 10, by1 + 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.line(image, (bx1, by1 + 24), (bx2, by1 + 24), (50, 50, 60), 1)

    # Telemetry rows
    if not analysis.telemetry_list:
        cv2.putText(
            image,
            "No subjects in field of view.",
            (bx1 + 12, by1 + 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.34,
            (140, 140, 140),
            1,
            cv2.LINE_AA,
        )
    else:
        y_offset = by1 + 42
        for t in analysis.telemetry_list[:4]:
            t_color = THREAT_COLORS[t.threat_level]["label"]
            line_str = (
                f"ID#{t.track_id}: Ang={t.spine_angle:.0f}° | "
                f"Spd={t.speed:.1f} | H/W={t.aspect_ratio:.1f} | {t.confirmed_behavior}"
            )
            cv2.putText(
                image,
                line_str,
                (bx1 + 10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.34,
                t_color,
                1,
                cv2.LINE_AA,
            )
            y_offset += 18

    # Separator above ticker
    ticker_sep_y = by2 - 28
    cv2.line(image, (bx1, ticker_sep_y), (bx2, ticker_sep_y), (50, 50, 60), 1)

    # Alert Ticker
    if analysis.recent_alerts:
        alert_msg = f"ALERT: {analysis.recent_alerts[0]}"
    else:
        alert_msg = "ALERT: STATUS: ALL MONITORED SUBJECTS STABLE"

    if len(alert_msg) > 52:
        alert_msg = alert_msg[:49] + "..."

    if "CRITICAL" in alert_msg:
        alert_color = (0, 0, 255)
    elif "HIGH" in alert_msg:
        alert_color = (0, 140, 255)
    elif "ELEVATED" in alert_msg or "MEDIUM" in alert_msg:
        alert_color = (0, 215, 255)
    else:
        alert_color = (0, 220, 0)

    cv2.putText(
        image,
        alert_msg,
        (bx1 + 10, by2 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.33,
        alert_color,
        1,
        cv2.LINE_AA,
    )

    return image
