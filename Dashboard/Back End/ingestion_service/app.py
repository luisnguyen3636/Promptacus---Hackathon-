import logging
import sys
from flask import Flask, jsonify
from .config import IngestionConfig, get_config
from .forwarder import ForwarderService, DLQManager
from .routes import ingestion_bp


def configure_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def create_app(config: IngestionConfig = None) -> Flask:
    """Application factory for CyberGuard Ingestion & Forwarding Gateway."""
    cfg = config or get_config()
    configure_logging("DEBUG" if cfg.GATEWAY_DEBUG else "INFO")

    app = Flask(__name__)
    app.config.from_object(cfg)

    # Initialize Forwarder & DLQ
    dlq_manager = DLQManager(storage_path=cfg.DLQ_STORAGE_PATH)
    forwarder_service = ForwarderService(config=cfg, dlq_manager=dlq_manager)

    app.extensions["forwarder_service"] = forwarder_service
    app.extensions["dlq_manager"] = dlq_manager

    # Register Blueprints
    app.register_blueprint(ingestion_bp)

    # Global Error Handlers
    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({"success": False, "error": "Bad Request", "message": str(e)}), 400

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"success": False, "error": "Endpoint Not Found", "message": str(e)}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({"success": False, "error": "Method Not Allowed. Use POST as specified in contract."}), 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        return jsonify({"success": False, "error": "Internal Server Error", "message": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    config = get_config()
    app.run(host=config.GATEWAY_HOST, port=config.GATEWAY_PORT, debug=config.GATEWAY_DEBUG)
