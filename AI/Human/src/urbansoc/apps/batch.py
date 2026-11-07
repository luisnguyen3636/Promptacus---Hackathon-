"""Batch offline video scanning and incident segment extraction application."""

import json
import logging
import os
from collections import Counter
from datetime import datetime
from typing import List, Optional

import cv2

from urbansoc.detection.yolo_pose import YOLOPoseDetector
from urbansoc.domain.schemas import HumanIncidentClip

logger = logging.getLogger("urbansoc.apps.batch")

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".wmv")


class BatchHumanDetector:
    """Offline batch analyzer processing pre-recorded video surveillance archives."""

    def __init__(
        self,
        records_dir: str = "records",
        output_dir: str = "output",
        model_weights: str = "yolo/yolo11n-pose.pt",
        device: Optional[str] = None,
        annotate_output: bool = True,
        conf_threshold: float = 0.25,
    ) -> None:
        self.records_dir = os.path.abspath(records_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.model_weights = model_weights
        self.device = device
        self.annotate_output = annotate_output
        self.conf_threshold = conf_threshold

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.records_dir, exist_ok=True)

        self.detector = YOLOPoseDetector(
            model_path=self.model_weights,
            device=self.device,
            conf_threshold=self.conf_threshold,
            output_dir=self.output_dir,
        )

    def process_all_videos(self) -> List[str]:
        """Scan records directory and analyze all discovered video files."""
        if not os.path.exists(self.records_dir):
            print(f"[BatchHumanDetector] Records directory '{self.records_dir}' does not exist.")
            return []

        all_files = os.listdir(self.records_dir)
        video_files = [
            os.path.join(self.records_dir, f)
            for f in sorted(all_files)
            if f.lower().endswith(VIDEO_EXTENSIONS)
        ]

        if not video_files:
            print(f"[BatchHumanDetector] No video files found in '{self.records_dir}'.")
            return []

        extracted_clips: List[str] = []
        for v_path in video_files:
            clips = self.process_single_video(v_path)
            extracted_clips.extend(clips)

        print(
            f"[BatchHumanDetector] Done: Extracted {len(extracted_clips)} "
            f"incident segment(s) to {self.output_dir}/"
        )
        return extracted_clips

    def process_single_video(self, video_path: str) -> List[str]:
        """Process a single video using streaming segment writers (no RAM exhaustion)."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[BatchHumanDetector] Error: Cannot open video '{video_path}'")
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        fps = 20.0 if raw_fps <= 0 or raw_fps > 120 else float(raw_fps)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        base_name = os.path.splitext(os.path.basename(video_path))[0]
        print(f"\n[BatchHumanDetector] Processing: {os.path.basename(video_path)}")
        print(f"  Resolution: {width}x{height} | FPS: {fps:.1f} | Frames: {total_frames}")

        extracted_segments: List[str] = []
        seg_counter = 0

        # Streaming segment writer state
        seg_writer: Optional[cv2.VideoWriter] = None
        temp_seg_path: Optional[str] = None
        seg_behaviors: List[str] = []
        seg_threats: List[str] = []
        seg_start_frame = 0
        seg_frame_count = 0

        frame_idx = 0
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        detection_events_path = os.path.join(self.output_dir, "detection_events.jsonl")

        def _finalize_segment(end_frame: int) -> None:
            nonlocal seg_writer, temp_seg_path, seg_behaviors, seg_threats, seg_start_frame, seg_frame_count
            if seg_writer is None or temp_seg_path is None:
                return

            seg_writer.release()
            seg_writer = None

            dominant_behavior = (
                Counter(seg_behaviors).most_common(1)[0][0]
                if seg_behaviors
                else "NORMAL"
            )
            dominant_threat = (
                Counter(seg_threats).most_common(1)[0][0]
                if seg_threats
                else "LOW"
            )

            final_name = f"{base_name}_seg{seg_counter}_{dominant_behavior}.mp4"
            final_path = os.path.join(self.output_dir, final_name)

            if os.path.exists(temp_seg_path):
                os.replace(temp_seg_path, final_path)

            extracted_segments.append(final_path)
            duration_sec = round(seg_frame_count / fps, 2)
            print(f"  -> Extracted incident segment: {final_name} ({seg_frame_count} frames, {duration_sec}s)")

            # Record incident metadata (Bug 11.12 resolution)
            clip_meta = HumanIncidentClip(
                event_id=f"INC-{base_name}-SEG{seg_counter:03d}",
                source_video=os.path.abspath(video_path),
                start_time=f"{seg_start_frame / fps:.2f}s",
                end_time=f"{end_frame / fps:.2f}s",
                start_frame=seg_start_frame,
                end_frame=end_frame,
                duration_seconds=duration_sec,
                output_filepath=os.path.abspath(final_path),
                primary_behavior=dominant_behavior,
                threat_level=dominant_threat,
            )

            try:
                with open(detection_events_path, mode="a", encoding="utf-8") as f:
                    record = {
                        "event_id": clip_meta.event_id,
                        "type": "BATCH_INCIDENT_SEGMENT",
                        "source_video": clip_meta.source_video,
                        "start_frame": clip_meta.start_frame,
                        "end_frame": clip_meta.end_frame,
                        "duration_seconds": clip_meta.duration_seconds,
                        "primary_behavior": clip_meta.primary_behavior,
                        "threat_level": clip_meta.threat_level,
                        "output_file": clip_meta.output_filepath,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error("Failed to write batch detection event: %s", e, exc_info=True)

            temp_seg_path = None
            seg_behaviors = []
            seg_threats = []
            seg_frame_count = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                frame_idx += 1
                video_timestamp = frame_idx / fps

                analysis, annotated_frame = self.detector.process_frame(
                    frame, frame_index=frame_idx, timestamp=video_timestamp
                )

                if frame_idx % 30 == 0:
                    pct = (frame_idx / total_frames * 100.0) if total_frames > 0 else 0.0
                    print(
                        f"  Frame {frame_idx}/{total_frames} ({pct:.0f}%) -> "
                        f"{analysis.human_count} human(s) | Threat: {analysis.highest_threat_level.value}"
                    )

                out_frame = annotated_frame if self.annotate_output else frame

                if analysis.has_human:
                    if seg_writer is None:
                        seg_counter += 1
                        seg_start_frame = frame_idx
                        temp_seg_path = os.path.join(
                            self.output_dir, f"{base_name}_seg{seg_counter}_TEMP.mp4"
                        )
                        seg_writer = cv2.VideoWriter(temp_seg_path, fourcc, fps, (width, height))
                        seg_frame_count = 0

                    seg_writer.write(out_frame)
                    seg_frame_count += 1
                    for h in analysis.humans:
                        seg_behaviors.append(h.behavior.primary_behavior.value)
                        seg_threats.append(h.behavior.threat_level.value)
                else:
                    if seg_writer is not None:
                        _finalize_segment(frame_idx)

            # Finalize trailing segment if ended while human present
            if seg_writer is not None:
                _finalize_segment(frame_idx)
        finally:
            cap.release()

        return extracted_segments

    def close(self) -> None:
        """Release underlying detector resources."""
        self.detector.close()
