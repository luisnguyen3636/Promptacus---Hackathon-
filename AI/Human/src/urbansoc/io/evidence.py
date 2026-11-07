"""Evidence Clip Recorder maintaining a pre-event rolling buffer and automatic incident export."""

import json
import logging
import os
import re
from collections import deque
from datetime import datetime
from typing import Deque, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("urbansoc.io.evidence")


class EvidenceClipRecorder:
    """Rolling pre-roll and post-roll video recorder saving MP4 incident evidence clips."""

    def __init__(
        self,
        output_dir: str = "output",
        fps: float = 20.0,
        frame_size: Tuple[int, int] = (640, 480),
        pre_roll_seconds: float = 1.5,
        post_roll_seconds: float = 2.0,
    ) -> None:
        self.output_dir = os.path.abspath(output_dir)
        self.fps = fps
        self.frame_size = frame_size
        self.pre_roll_limit = max(1, int(round(fps * pre_roll_seconds)))
        self.post_roll_limit = max(1, int(round(fps * post_roll_seconds)))

        os.makedirs(self.output_dir, exist_ok=True)
        self.events_jsonl_path = os.path.join(self.output_dir, "detection_events.jsonl")

        self.pre_roll_buffer: Deque[np.ndarray] = deque(maxlen=self.pre_roll_limit)
        self.is_recording = False
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_clip_path: Optional[str] = None
        self.clip_frame_count = 0
        self.cooldown_counter = 0
        self.event_counter = 0

        self.clip_start_time = ""
        self.clip_start_dt = ""

    def update(
        self,
        frame: np.ndarray,
        is_event_active: bool,
        timestamp_str: Optional[str] = None,
    ) -> Optional[str]:
        """Feed current frame and trigger state into evidence recorder state machine.

        Returns:
            Path to saved clip if finalized in this frame, else None.
        """
        now_str = (
            timestamp_str
            if timestamp_str
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        )

        finalized_path: Optional[str] = None

        if is_event_active:
            if not self.is_recording:
                self._start_recording(now_str)

            if self.writer is not None:
                self.writer.write(frame)
                self.clip_frame_count += 1
                self.cooldown_counter = 0
        else:
            if self.is_recording:
                # In post-roll grace period
                if self.writer is not None:
                    self.writer.write(frame)
                    self.clip_frame_count += 1
                    self.cooldown_counter += 1

                if self.cooldown_counter >= self.post_roll_limit:
                    finalized_path = self._finalize_clip(now_str)
            else:
                self.pre_roll_buffer.append(frame.copy())

        return finalized_path

    def _start_recording(self, timestamp_str: str) -> None:
        self.event_counter += 1
        clean_ts = re.sub(r"[^0-9]", "", timestamp_str)[:14]
        if len(clean_ts) < 14:
            clean_ts = datetime.now().strftime("%Y%m%d%H%M%S")

        formatted_ts = f"{clean_ts[:8]}_{clean_ts[8:14]}"
        filename = f"EVIDENCE_{formatted_ts}_HUMAN.mp4"
        self.current_clip_path = os.path.join(self.output_dir, filename)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(
            self.current_clip_path,
            fourcc,
            float(self.fps),
            (int(self.frame_size[0]), int(self.frame_size[1])),
        )

        # Flush pre-roll buffer into writer
        self.clip_frame_count = 0
        for pre_frame in self.pre_roll_buffer:
            self.writer.write(pre_frame)
            self.clip_frame_count += 1
        self.pre_roll_buffer.clear()

        self.clip_start_time = timestamp_str
        self.clip_start_dt = clean_ts
        self.is_recording = True
        self.cooldown_counter = 0
        logger.info(">>> TRIGGERED RECORDING: %s", self.current_clip_path)

    def _finalize_clip(self, end_timestamp_str: str) -> Optional[str]:
        if not self.is_recording or self.writer is None or not self.current_clip_path:
            return None

        saved_path = self.current_clip_path
        self.writer.release()
        self.writer = None
        self.is_recording = False

        duration_sec = (
            round(self.clip_frame_count / self.fps, 2) if self.fps > 0 else 0.0
        )
        event_id = f"EVT-{self.clip_start_dt}-{self.event_counter:03d}"

        # Write metadata entry to detection_events.jsonl
        record = {
            "event_id": event_id,
            "type": "HUMAN_PRESENCE_DETECTED",
            "start_time": self.clip_start_time,
            "end_time": end_timestamp_str,
            "duration_seconds": duration_sec,
            "frame_count": self.clip_frame_count,
            "output_file": os.path.abspath(saved_path),
        }

        try:
            with open(self.events_jsonl_path, mode="a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to write detection event JSONL: %s", e, exc_info=True)

        logger.info("<<< SAVED EVIDENCE CLIP: %s (%s frames, %ss)", saved_path, self.clip_frame_count, duration_sec)
        self.current_clip_path = None
        self.clip_frame_count = 0
        self.cooldown_counter = 0
        return saved_path

    def release(self) -> None:
        """Safely flush and finalize recording upon shutdown."""
        if self.is_recording:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self._finalize_clip(now_str)
