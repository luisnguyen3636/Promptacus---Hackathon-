#!/usr/bin/env python3
"""
Entrypoint script for running the CyberGuard Ingestion & Forwarding Gateway.
"""
from app import create_app, get_config

if __name__ == "__main__":
    config = get_config()
    app = create_app(config)
    print(f"🚀 Starting CyberGuard Ingestion Gateway on http://{config.GATEWAY_HOST}:{config.GATEWAY_PORT}")
    print(f"🔗 Forwarding target configured to: {config.TARGET_SERVER_BASE_URL}")
    app.run(host=config.GATEWAY_HOST, port=config.GATEWAY_PORT, debug=config.GATEWAY_DEBUG)
