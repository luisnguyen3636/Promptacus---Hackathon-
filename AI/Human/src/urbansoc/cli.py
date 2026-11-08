"""Command-line interface and entrypoint dispatcher for Urban Safety AI-SOC."""

import argparse
import os
import sys
from typing import Optional

from urbansoc.apps.batch import BatchHumanDetector
from urbansoc.apps.live import CameraRecorder
from urbansoc.domain.webhook_models import CameraLocationConfig


def create_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser with SOC-grade help descriptions."""
    parser = argparse.ArgumentParser(
        description="Urban Safety AI-SOC: Human Detection, Pose Estimation & Behavior Recognition",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["live", "batch", "server", "client"],
        default="live",
        help="Operating mode:\n"
             "  live   = Real-time camera feed analysis (default)\n"
             "  batch  = Offline batch scan across video files in records/\n"
             "  server = Central intermediate multi-camera inference server\n"
             "  client = Edge camera client streaming to central server",
    )
    parser.add_argument(
        "--camera",
        type=str,
        default="0",
        help="Camera device index (default: 0) or path to a video file for simulation",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="yolo/yolo11n-pose.pt",
        help="Path to YOLO11-Pose model weights (default: yolo/yolo11n-pose.pt)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Inference compute device: 'cpu', 'cuda', or auto-detect (default: None)",
    )
    parser.add_argument(
        "--record-all",
        action="store_true",
        default=False,
        help="Record continuous full session to records/ (default: False)",
    )
    parser.add_argument(
        "--records-dir",
        type=str,
        default="records",
        help="Directory for batch input videos and full session recordings (default: records)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory for audit logs, snapshots, and incident clips (default: output)",
    )
    parser.add_argument(
        "--conf-thresh",
        type=float,
        default=0.25,
        help="Object and keypoint detection confidence threshold (default: 0.25)",
    )
    parser.add_argument(
        "--webhook-url",
        type=str,
        default=os.environ.get("URBANSOC_WEBHOOK_URL", None),
        help="Target server URL to POST incident event metadata (default: None or URBANSOC_WEBHOOK_URL)",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default="CAM_01",
        help="Unique camera identifier (default: CAM_01)",
    )
    parser.add_argument(
        "--camera-name",
        type=str,
        default="Camera Giám Sát Trung Tâm",
        help="Descriptive name of the camera (default: Camera Giám Sát Trung Tâm)",
    )
    parser.add_argument(
        "--camera-lat",
        type=float,
        default=10.776889,
        help="Camera GPS latitude (default: 10.776889)",
    )
    parser.add_argument(
        "--camera-lon",
        type=float,
        default=106.700806,
        help="Camera GPS longitude (default: 106.700806)",
    )
    parser.add_argument(
        "--camera-address",
        type=str,
        default="Khu vực Trung Tâm",
        help="Physical address/zone of camera installation (default: Khu vực Trung Tâm)",
    )
    parser.add_argument(
        "--webhook-min-threat",
        type=str,
        choices=["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default="ALL",
        help="Minimum threat level required to trigger HTTP POST (default: ALL)",
    )
    parser.add_argument(
        "--webhook-cooldown",
        type=float,
        default=3.0,
        help="Cooldown in seconds between successive POSTs for the same track (default: 3.0)",
    )
    parser.add_argument(
        "--webhook-min-conf",
        type=float,
        default=0.35,
        help="Anti-noise filter: minimum detection confidence to allow webhook push (default: 0.35)",
    )
    parser.add_argument(
        "--webhook-min-bbox-area",
        type=int,
        default=1200,
        help="Anti-noise filter: minimum bounding box pixel area to avoid distant noise (default: 1200)",
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://localhost:7777",
        help="Intermediate server URL for client streaming (default: http://localhost:7777)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Server port to bind when running in --mode server (default: 7777)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run without local GUI preview window (default: False)",
    )
    parser.add_argument(
        "--webhook-no-filter-noise",
        action="store_true",
        default=False,
        help="Disable anti-noise filtering (default: False)",
    )

    return parser


def print_banner(args: argparse.Namespace) -> None:
    """Print the standardized SOC startup banner."""
    print("=" * 70)
    print("URBAN SAFETY AI-SOC: HUMAN DETECTION & BEHAVIOR MONITOR")
    print("=" * 70)
    print(f"Mode:        {args.mode.upper()}")
    print(f"Weights:     {args.weights}")
    print(f"Device:      {args.device if args.device else 'auto-detect'}")
    print(f"Conf Thresh: {args.conf_thresh}")
    print(f"Output Dir:  {os.path.abspath(args.output_dir)}")
    if args.webhook_url:
        print(f"Webhook URL: {args.webhook_url} (Min Threat: {args.webhook_min_threat})")
        print(f"Camera Info: ID={args.camera_id} [{args.camera_name}] ({args.camera_lat}, {args.camera_lon})")
    if args.mode == "batch":
        print(f"Records Dir: {os.path.abspath(args.records_dir)}")
    else:
        print(f"Camera Idx:  {args.camera}")
        print(f"Record All:  {args.record_all}")
    print("=" * 70)


def main(argv: Optional[list] = None) -> int:
    """Main CLI execution handler."""
    parser = create_parser()
    args = parser.parse_args(argv)

    print_banner(args)

    camera_cfg = CameraLocationConfig(
        camera_id=args.camera_id,
        name=args.camera_name,
        address=args.camera_address,
        latitude=args.camera_lat,
        longitude=args.camera_lon,
    )

    cam_target = int(args.camera) if args.camera.isdigit() else args.camera

    if args.mode == "live":
        app = CameraRecorder(
            camera_index=cam_target,
            record_full_session=args.record_all,
            model_weights=args.weights,
            device=args.device,
            min_confidence=args.conf_thresh,
            output_dir=args.output_dir,
            records_dir=args.records_dir,
            webhook_url=args.webhook_url,
            camera_config=camera_cfg,
            webhook_min_threat=args.webhook_min_threat,
            webhook_cooldown=args.webhook_cooldown,
            webhook_min_conf=args.webhook_min_conf,
            webhook_min_bbox_area=args.webhook_min_bbox_area,
            webhook_filter_noise=(not args.webhook_no_filter_noise),
        )
        app.record_video()
    elif args.mode == "batch":
        batch_app = BatchHumanDetector(
            records_dir=args.records_dir,
            output_dir=args.output_dir,
            model_weights=args.weights,
            device=args.device,
            conf_threshold=args.conf_thresh,
        )
        batch_app.process_all_videos()
    elif args.mode == "server":
        from urbansoc.server.inference_server import InferenceServer
        server = InferenceServer(
            port=args.port,
            model_weights=args.weights,
            device=args.device,
            conf_threshold=args.conf_thresh,
            output_dir=args.output_dir,
            webhook_url=args.webhook_url,
            webhook_min_threat=args.webhook_min_threat,
            webhook_cooldown=args.webhook_cooldown,
            webhook_filter_noise=(not args.webhook_no_filter_noise),
        )
        server.start(blocking=True)
    elif args.mode == "client":
        from urbansoc.client.edge_client import EdgeCameraClient
        client = EdgeCameraClient(
            server_url=args.server_url,
            camera_id=args.camera_id,
            camera_name=args.camera_name,
            camera_index=cam_target,
            lat=args.camera_lat,
            lon=args.camera_lon,
            address=args.camera_address,
            headless=args.headless,
        )
        client.stream_loop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
