"""Command-line interface and entrypoint dispatcher for Urban Safety AI-SOC."""

import argparse
import os
import sys
from typing import Optional

from urbansoc.apps.batch import BatchHumanDetector
from urbansoc.apps.live import CameraRecorder


def create_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser with SOC-grade help descriptions."""
    parser = argparse.ArgumentParser(
        description="Urban Safety AI-SOC: Human Detection, Pose Estimation & Behavior Recognition",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["live", "batch"],
        default="live",
        help="Operating mode:\n"
             "  live  = Real-time camera feed analysis (default)\n"
             "  batch = Offline batch scan across video files in records/",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index (default: 0)",
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

    if args.mode == "live":
        app = CameraRecorder(
            camera_index=args.camera,
            record_full_session=args.record_all,
            model_weights=args.weights,
            device=args.device,
            min_confidence=args.conf_thresh,
            output_dir=args.output_dir,
            records_dir=args.records_dir,
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
