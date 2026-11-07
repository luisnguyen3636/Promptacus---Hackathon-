#!/usr/bin/env python3
"""Dedicated Urban Safety AI-SOC Webhook Test Server.

Extends SimpleHTTPRequestHandler to serve web files for GET
and accept incident event payloads for POST on port 8000.
"""

import base64
import http.server
import json
import os
import sys
from datetime import datetime


class IncidentWebhookHandler(http.server.SimpleHTTPRequestHandler):
    """Dual HTTP handler: GET serves directory files, POST accepts incident payloads."""

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
            event_id = payload.get("event_id", f"EVT_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            timestamp = payload.get("timestamp")
            camera = payload.get("camera", {})
            detection = payload.get("detection", {})
            weapon = detection.get("weapon", {})
            subjects = detection.get("subjects", [])
            full_img = detection.get("full_image", {})

            print("\n" + "=" * 70)
            print("🚨 [SERVER 8000] RECEIVED INCIDENT POST WEBHOOK EVENT!")
            print("=" * 70)
            print(f"• Event ID:        {event_id}")
            print(f"• Timestamp:       {timestamp} (Epoch: {payload.get('timestamp_ms')})")
            print(f"• Camera ID:       {camera.get('camera_id')} - {camera.get('name')}")
            print(f"• Camera Location: Lat={camera.get('latitude')}, Lon={camera.get('longitude')}")
            print(f"• Camera Address:  {camera.get('address')}")
            print(f"• Primary Action:  {detection.get('primary_action')}")
            print(f"• Threat Level:    {detection.get('threat_level')} (Score: {detection.get('threat_score')})")
            print(f"• Urgent Flag:     {detection.get('is_urgent')}")
            print(f"• Reasoning:       {detection.get('reasoning')}")
            print(f"• Weapon Detected: {weapon.get('is_weapon_detected')} (Types: {weapon.get('weapon_types')})")
            print(f"• Total Subjects:  {len(subjects)}")

            save_dir = os.path.abspath(os.path.join("output", "received_webhooks"))
            os.makedirs(save_dir, exist_ok=True)

            for s in subjects:
                track_id = s.get("track_id")
                role = s.get("role")
                b_name = s.get("behavior")
                score = s.get("threat_score")
                crop_b64 = s.get("crop_image_base64", "")
                has_crop = bool(crop_b64)
                print(f"   ▶ Track #{track_id}: Role={role} | Behavior={b_name} | Score={score} | CropBase64={has_crop}")

                # Save cropped image file if base64 present
                if crop_b64 and "," in crop_b64:
                    raw_b64 = crop_b64.split(",", 1)[1]
                    crop_bytes = base64.b64decode(raw_b64)
                    crop_filename = f"{event_id}_track_{track_id}_crop.jpg"
                    crop_filepath = os.path.join(save_dir, crop_filename)
                    with open(crop_filepath, "wb") as cf:
                        cf.write(crop_bytes)

            full_b64 = full_img.get("image_base64", "")
            print(f"• Full Frame:      {full_img.get('width')}x{full_img.get('height')} | Base64 Length={len(full_b64)} bytes")

            # Save full image file if base64 present
            if full_b64 and "," in full_b64:
                raw_b64 = full_b64.split(",", 1)[1]
                full_bytes = base64.b64decode(raw_b64)
                full_filename = f"{event_id}_full_frame.jpg"
                full_filepath = os.path.join(save_dir, full_filename)
                with open(full_filepath, "wb") as ff:
                    ff.write(full_bytes)

            # Save full raw JSON event
            json_filepath = os.path.join(save_dir, f"{event_id}.json")
            with open(json_filepath, "w", encoding="utf-8") as jf:
                json.dump(payload, jf, ensure_ascii=False, indent=2)

            print(f"💾 Saved Event Data & Images to: {save_dir}/")
            print("=" * 70 + "\n")

            response_data = {
                "status": "success",
                "message": "Incident payload received and stored successfully",
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
    print("=" * 70)
    print(f"🌐 [AI-SOC WEBHOOK SERVER] Listening on http://0.0.0.0:{port}")
    print("   • GET:  Serves web browser files & status")
    print("   • POST: Receives incident events with full metadata & crops")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port_arg)
