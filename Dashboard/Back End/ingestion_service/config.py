import os
from dataclasses import dataclass

@dataclass
class IngestionConfig:
    """Configuration settings for CyberGuard Ingestion & Forwarding Gateway."""
    GATEWAY_HOST: str = os.getenv("GATEWAY_HOST", "0.0.0.0")
    GATEWAY_PORT: int = int(os.getenv("GATEWAY_PORT", "5000"))
    GATEWAY_DEBUG: bool = os.getenv("GATEWAY_DEBUG", "false").lower() in ("true", "1")

    # Upstream Target Server Destination
    TARGET_SERVER_BASE_URL: str = os.getenv("TARGET_SERVER_BASE_URL", "http://127.0.0.1:5001")
    TARGET_SERVER_TIMEOUT_MS: int = int(os.getenv("TARGET_SERVER_TIMEOUT_MS", "3000"))
    TARGET_SERVER_MAX_RETRIES: int = int(os.getenv("TARGET_SERVER_MAX_RETRIES", "3"))
    TARGET_SERVER_API_KEY: str = os.getenv("TARGET_SERVER_API_KEY", "cyberguard-soc-internal-secret")

    # Forwarding & Reliability
    FORWARD_MODE: str = os.getenv("FORWARD_MODE", "sync")  # "sync" or "async"
    DLQ_STORAGE_PATH: str = os.getenv("DLQ_STORAGE_PATH", "./data/dlq")
    ENABLE_DEAD_LETTER_QUEUE: bool = os.getenv("ENABLE_DEAD_LETTER_QUEUE", "true").lower() in ("true", "1")
    SOC_ENVIRONMENT: str = os.getenv("SOC_ENVIRONMENT", "development")

def get_config() -> IngestionConfig:
    return IngestionConfig()
