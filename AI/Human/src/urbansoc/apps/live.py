"""Live camera surveillance application with interactive SOC HUD and hotkey controls."""

import logging
import os
import time
from datetime import datetime
from typing import Optional, Tuple, Union

import cv2
import numpy as np

from urbansoc.detection.yolo_pose import YOLOPoseDetector
from urbansoc.domain.webhook_models import CameraLocationConfig
from urbansoc.io.evidence import EvidenceClipRecorder
from urbansoc.io.sources import CameraSource
from urbansoc.telemetry.webhook_dispatcher import WebhookDispatcher

logger = logging.getLogger("urbansoc.apps.live")


class CameraRecorder:
    """Real-time camera surveillance application with interactive OpenCV GUI."""

    def __init__(
        self,
        camera_index: Union[int, str] = 0,
        resolution: Tuple[int, int] = (640, 480),
        record_full_session: bool = False,
        auto_extract_evidence: bool = True,
        model_weights: str = "yolo/yolo11n-pose.pt",
        device: Optional[str] = None,
        min_confidence: float = 0.25,
        output_dir: str = "output",
        records_dir: str = "records",
        fps: float = 20.0,
        webhook_url: Optional[str] = None,
        camera_config: Optional[CameraLocationConfig] = None,
        webhook_min_threat: str = "ALL",
        webhook_cooldown: float = 3.0,
        webhook_min_conf: float = 0.35,
        webhook_min_bbox_area: int = 1200,
        webhook_filter_noise: bool = True,
    ) -> None:
        self.camera_index = camera_index
        self.resolution = resolution
        self.record_full_session = record_full_session
        self.auto_extract_evidence = auto_extract_evidence
        self.model_weights = model_weights
        self.device = device
        self.min_confidence = min_confidence
        self.output_dir = os.path.abspath(output_dir)
        self.records_dir = os.path.abspath(records_dir)
        self.fps = fps
        self.webhook_url = webhook_url
        self.camera_config = camera_config if camera_config is not None else CameraLocationConfig()

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.records_dir, exist_ok=True)

        self.show_skeleton = True
        self.session_writer: Optional[cv2.VideoWriter] = None

        # 1. Initialize Video Source (Non-blocking queue)
        self.source = CameraSource(
            camera_index=self.camera_index,
            resolution=self.resolution,
            fps=self.fps,
        )
        self.frame_size = self.source.frame_size

        # 2. Initialize Pose & Behavior Detector
        self.detector = YOLOPoseDetector(
            model_path=self.model_weights,
            device=self.device,
            conf_threshold=self.min_confidence,
            fps=self.fps,
            output_dir=self.output_dir,
        )

        # 3. Initialize Evidence Clip Recorder
        self.evidence_recorder = EvidenceClipRecorder(
            output_dir=self.output_dir,
            fps=self.fps,
            frame_size=self.frame_size,
            pre_roll_seconds=1.5,
            post_roll_seconds=2.0,
        )

        # 4. Initialize Asynchronous HTTP POST Webhook Dispatcher
        self.webhook_dispatcher = WebhookDispatcher(
            server_url=self.webhook_url,
            camera_config=self.camera_config,
            min_threat_level=webhook_min_threat,
            cooldown_seconds=webhook_cooldown,
            min_detection_conf=webhook_min_conf,
            min_bbox_area=webhook_min_bbox_area,
            filter_noise=webhook_filter_noise,
        )

        if self.record_full_session:
            self._start_session_recorder()

    def _start_session_recorder(self) -> None:
        now_clean = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SESSION_{now_clean}_FULL.mp4"
        path = os.path.join(self.records_dir, filename)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.session_writer = cv2.VideoWriter(
            path, fourcc, self.fps, (int(self.frame_size[0]), int(self.frame_size[1]))
        )
        print(f"[CameraRecorder] Continuous session recording started: {path}")

    def _stop_session_recorder(self) -> None:
        if self.session_writer is not None:
            self.session_writer.release()
            self.session_writer = None
            print("[CameraRecorder] Continuous session recording stopped.")

    def record_video(self) -> None:
        """Main execution loop for real-time video capture, inference, and GUI rendering."""
        window_name = "Urban Safety AI-SOC: Human Behavior & Pose Monitor"
        has_gui = True
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, self.frame_size[0], self.frame_size[1])
        except Exception:
            has_gui = False
            print("[CameraRecorder] Note: No graphical display detected. Running in headless mode.")

        print("=" * 70)
        print("URBAN SAFETY AI-SOC: HUMAN POSE & BEHAVIOR MONITOR")
        print(f"Mode: Live Camera | Resolution: {self.frame_size[0]}x{self.frame_size[1]}")
        print(f"Output: {self.output_dir} | Records: {self.records_dir}")
        print("Hotkeys:")
        print("  [q] Quit & finalize recordings")
        print("  [s] Save high-res snapshot")
        print("  [h] Toggle HUD & skeleton overlays")
        print("  [d] Toggle Diagnostic Telemetry Alert Box")
        print("  [r] Toggle continuous session recording")
        print("=" * 70)

        frame_index = 0
        try:
            while True:
                ret, frame = self.source.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                frame_index += 1
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

                # 1. AI & Behavior inference
                if self.show_skeleton:
                    analysis, display_frame = self.detector.process_frame(frame, frame_index)
                else:
                    display_frame = frame.copy()
                    analysis = None

                is_human = analysis.has_human if analysis else False

                # 2. Reflect recording state before updating clip recorder
                if analysis:
                    analysis.is_recording_evidence = self.evidence_recorder.is_recording

                # 3. Evidence recording update
                if self.auto_extract_evidence:
                    saved_clip = self.evidence_recorder.update(display_frame, is_human, now_str)
                    if saved_clip:
                        print(f"[CameraRecorder] Evidence clip finalized: {saved_clip}")

                # 4. Asynchronous Webhook Event Dispatching (Non-blocking)
                if analysis and self.webhook_dispatcher.is_enabled:
                    self.webhook_dispatcher.dispatch_frame_event(
                        frame=frame,
                        annotated_frame=display_frame,
                        analysis_result=analysis,
                    )

                # 5. Continuous session recording
                if self.session_writer is not None:
                    self.session_writer.write(display_frame)

                # 6. Display GUI
                if has_gui:
                    try:
                        cv2.imshow(window_name, display_frame)
                        key = cv2.waitKey(1) & 0xFF
                    except Exception:
                        has_gui = False
                        key = -1
                else:
                    time.sleep(1.0 / self.fps)
                    key = -1

                # 6. Hotkey handling
                if key == ord("q"):
                    print("[CameraRecorder] Stopping camera recorder...")
                    break
                elif key == ord("s"):
                    snap_name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    snap_path = os.path.join(self.output_dir, snap_name)
                    cv2.imwrite(snap_path, display_frame)
                    print(f"[CameraRecorder] Snapshot saved: {snap_path}")
                elif key == ord("h"):
                    self.show_skeleton = not self.show_skeleton
                    state_str = "ON" if self.show_skeleton else "OFF"
                    print(f"[CameraRecorder] HUD overlay: {state_str}")
                elif key == ord("d"):
                    if hasattr(self.detector, "toggle_debug_box"):
                        box_state = self.detector.toggle_debug_box()
                        state_str = "ON" if box_state else "OFF"
                        print(f"[CameraRecorder] Diagnostic Alert Box Debug: {state_str}")
                elif key == ord("r"):
                    if self.session_writer is None:
                        self._start_session_recorder()
                    else:
                        self._stop_session_recorder()
        except KeyboardInterrupt:
            print("\n[CameraRecorder] Interrupted by user.")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Release all camera, video writer, and window resources."""
        self.source.release()
        self._stop_session_recorder()
        self.evidence_recorder.release()
        self.webhook_dispatcher.shutdown()
        self.detector.close()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
