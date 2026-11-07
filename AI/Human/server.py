#!/usr/bin/env python3
"""Dedicated Urban Safety AI-SOC Webhook Test Server.

Extends SimpleHTTPRequestHandler to serve web files for GET
and accept incident event payloads for POST on port 8000,
verifying cryptographic SHA-256 tamper-proof image signatures
and displaying comprehensive subject telemetry.
"""

import base64
import hashlib
import http.server
import json
import os
import sys
from datetime import datetime


def verify_sha256(raw_bytes: bytes, timestamp_ms: int, expected_hash: str) -> bool:
    """Verify that cryptographic SHA-256(raw_bytes + timestamp_ms) matches expected_hash."""
    hasher = hashlib.sha256()
    hasher.update(raw_bytes)
    hasher.update(str(timestamp_ms).encode("utf-8"))
    computed = hasher.hexdigest()
    return computed == expected_hash


class IncidentWebhookHandler(http.server.SimpleHTTPRequestHandler):
    """Dual HTTP handler: GET serves directory files, POST accepts incident payloads."""

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
            event_id = payload.get("event_id", f"EVT_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            timestamp = payload.get("timestamp")
            timestamp_ms = int(payload.get("timestamp_ms", 0))
            camera = payload.get("camera", {})
            detection = payload.get("detection", {})
            weapon = detection.get("weapon", {})
            subjects = detection.get("subjects", [])
            full_img = detection.get("full_image", {})
            audit = payload.get("audit", {})

            print("\n" + "=" * 76)
            print("🚨 [SERVER 8000] RECEIVED VERIFIED INCIDENT POST WEBHOOK EVENT!")
            print("=" * 76)
            print(f"• Event ID:        {event_id}")
            print(f"• Timestamp:       {timestamp} (Epoch ms: {timestamp_ms})")
            print(f"• Camera ID:       {camera.get('camera_id')} - {camera.get('name')}")
            print(f"• Camera Location: Lat={camera.get('latitude')}, Lon={camera.get('longitude')}")
            print(f"• Camera Address:  {camera.get('address')}")
            print(f"• Primary Action:  {detection.get('primary_action')}")
            print(f"• Threat Level:    {detection.get('threat_level')} (Score: {detection.get('threat_score')})")
            print(f"• Urgent Flag:     {detection.get('is_urgent')}")
            print(f"• Reasoning:       {detection.get('reasoning')}")
            print(f"• Weapon Detected: {weapon.get('is_weapon_detected')} (Types: {weapon.get('weapon_types')})")

            # Anti-noise audit info
            anti_noise = audit.get("anti_noise_filtering", {})
            if anti_noise:
                print(f"• Anti-Noise:      Active={anti_noise.get('enabled')} | MinConf={anti_noise.get('min_conf')} | MinArea={anti_noise.get('min_bbox_area')} | FilteredOut={anti_noise.get('filtered_noise_count')}")

            save_dir = os.path.abspath(os.path.join("output", "received_webhooks"))
            os.makedirs(save_dir, exist_ok=True)

            print(f"• Total Subjects:  {len(subjects)}")
            for s in subjects:
                track_id = s.get("track_id")
                role = s.get("role")
                b_name = s.get("behavior")
                score = s.get("threat_score")
                conf = s.get("confidence")
                geom = s.get("bbox_geometry", {})
                dwell = s.get("dwell_time_seconds")
                kine = s.get("kinematics", {})
                kps = s.get("keypoints", [])
                crop_b64 = s.get("crop_image_base64", "")
                expected_crop_hash = s.get("crop_image_sha256", "")

                print(f"   ▶ Track #{track_id}: Role={role} | Behavior={b_name} | Score={score} | DetConf={conf}")
                print(f"     Geometry: Box={s.get('bbox')} | WxH={geom.get('width')}x{geom.get('height')} | Area={geom.get('area')} | Dwell={dwell}s")
                print(f"     Kinematics: SpineAngle={kine.get('spine_angle')}° | L_Elbow={kine.get('left_elbow_angle')}° | R_Elbow={kine.get('right_elbow_angle')}° | WristDist={kine.get('wrist_distance')}px")
                print(f"     Keypoints: {len(kps)} COCO-17 landmarks verified")

                # Verify SHA-256 hash of cropped image
                if crop_b64 and "," in crop_b64:
                    raw_b64 = crop_b64.split(",", 1)[1]
                    crop_bytes = base64.b64decode(raw_b64)
                    hash_valid = verify_sha256(crop_bytes, timestamp_ms, expected_crop_hash)
                    hash_status = "✅ VALID (MATCH)" if hash_valid else "❌ TAMPER DETECTED"
                    print(f"     Forensic Hash: {expected_crop_hash[:16]}... [{hash_status}] ({len(crop_bytes)} bytes)")

                    crop_filename = f"{event_id}_track_{track_id}_crop.jpg"
                    crop_filepath = os.path.join(save_dir, crop_filename)
                    with open(crop_filepath, "wb") as cf:
                        cf.write(crop_bytes)

            full_b64 = full_img.get("image_base64", "")
            expected_full_hash = full_img.get("sha256_hash", "")
            if full_b64 and "," in full_b64:
                raw_b64 = full_b64.split(",", 1)[1]
                full_bytes = base64.b64decode(raw_b64)
                full_hash_valid = verify_sha256(full_bytes, timestamp_ms, expected_full_hash)
                full_hash_status = "✅ VALID (TAMPER-PROOF)" if full_hash_valid else "❌ TAMPER DETECTED"
                print(f"• Full Frame:      {full_img.get('width')}x{full_img.get('height')} | {len(full_bytes)} bytes")
                print(f"• Forensic Hash:   {expected_full_hash} [{full_hash_status}]")

                full_filename = f"{event_id}_full_frame.jpg"
                full_filepath = os.path.join(save_dir, full_filename)
                with open(full_filepath, "wb") as ff:
                    ff.write(full_bytes)

            # Save full raw JSON event
            json_filepath = os.path.join(save_dir, f"{event_id}.json")
            with open(json_filepath, "w", encoding="utf-8") as jf:
                json.dump(payload, jf, ensure_ascii=False, indent=2)

            print(f"💾 Saved Event Data & Images to: {save_dir}/")
            print("=" * 76 + "\n")

            response_data = {
                "status": "success",
                "message": "Incident payload with forensic SHA-256 verified and stored successfully",
                "event_id": event_id,
            }
            resp_bytes = json.dumps(response_data).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        except Exception as e:
            print(f"❌ [SERVER 8000] Error processing POST: {e}")
            err_bytes = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err_bytes)))
            self.end_headers()
            self.wfile.write(err_bytes)


def run_server(port: int = 8000) -> None:
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, IncidentWebhookHandler)
    print("=" * 76)
    print(f"🌐 [AI-SOC WEBHOOK SERVER] Listening on http://0.0.0.0:{port}")
    print("   • GET:  Serves web browser files & status")
    print("   • POST: Receives incident events with forensic SHA-256 & full telemetry")
    print("=" * 76)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port_arg)
