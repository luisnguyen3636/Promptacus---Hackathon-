"""
Mock Target Server to simulate the Central SOC Backend / Downstream Server.
Used for end-to-end integration testing and verification of the Forwarding Gateway.
"""
from flask import Flask, request, jsonify

received_requests = []


def create_mock_target_app() -> Flask:
    app = Flask("mock_target_server")

    @app.before_request
    def record_request():
        received_requests.append({
            "path": request.path,
            "method": request.method,
            "headers": dict(request.headers),
            "json": request.get_json(silent=True),
        })

    @app.route("/api/soc/session", methods=["POST"])
    def target_session():
        return jsonify({"status": "SUCCESS", "module": "session", "ack": True}), 200

    @app.route("/api/soc/config/system", methods=["POST"])
    def target_config_system():
        return jsonify({"status": "SUCCESS", "module": "system_config", "ack": True}), 200

    @app.route("/api/devices/cameras/config", methods=["POST"])
    def target_camera_config():
        return jsonify({"status": "SUCCESS", "module": "camera_config", "count": len(request.get_json() or [])}), 200

    @app.route("/api/soc/live/meta", methods=["POST"])
    def target_live_meta():
        return jsonify({"status": "SUCCESS", "module": "live_meta", "ack": True}), 200

    @app.route("/api/soc/live/system", methods=["POST"])
    def target_live_system():
        return jsonify({"status": "SUCCESS", "module": "live_system", "ack": True}), 200

    @app.route("/api/soc/threat-overview", methods=["POST"])
    def target_threat_overview():
        return jsonify({"status": "SUCCESS", "module": "threat_overview", "ack": True}), 200

    @app.route("/api/soc/kpi", methods=["POST"])
    def target_kpi():
        return jsonify({"status": "SUCCESS", "module": "kpi", "ack": True}), 200

    @app.route("/api/soc/infrastructure", methods=["POST"])
    def target_infrastructure():
        return jsonify({"status": "SUCCESS", "module": "infrastructure", "ack": True}), 200

    @app.route("/api/devices/cameras/matrix", methods=["POST"])
    def target_camera_matrix():
        return jsonify({"status": "SUCCESS", "module": "camera_matrix", "ack": True}), 200

    @app.route("/api/incidents/recent", methods=["POST"])
    def target_recent_incidents():
        return jsonify({"status": "SUCCESS", "module": "recent_incidents", "ack": True}), 200

    @app.route("/api/soc/full-sync", methods=["POST"])
    def target_full_sync():
        return jsonify({"status": "SUCCESS", "module": "full_sync", "ack": True}), 200

    @app.route("/api/test/error-500", methods=["POST"])
    def target_error_500():
        return jsonify({"error": "Simulated upstream failure"}), 500

    @app.route("/_received", methods=["GET"])
    def get_received():
        return jsonify(received_requests)

    @app.route("/_clear", methods=["POST"])
    def clear_received():
        received_requests.clear()
        return jsonify({"cleared": True})

    return app
