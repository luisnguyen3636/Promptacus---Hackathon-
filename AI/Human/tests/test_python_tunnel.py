"""Unit tests for native Python Cloudflare Tunnel Manager."""

import re
import pytest
from urbansoc.server.tunnel import CloudflareTunnelManager


def test_cloudflare_tunnel_manager_init():
    """Verify CloudflareTunnelManager initializes with proper defaults."""
    mgr = CloudflareTunnelManager(local_port=8000, local_host="127.0.0.1")
    assert mgr.local_port == 8000
    assert mgr.local_host == "127.0.0.1"
    assert mgr.public_url is None
    assert mgr.process is None


def test_cloudflare_tunnel_regex_extraction():
    """Verify regex correctly parses trycloudflare.com URLs from logs."""
    sample_log = (
        "2026-11-07T15:45:10Z INF +--------------------------------------------------------------------------------------------+\n"
        "2026-11-07T15:45:10Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |\n"
        "2026-11-07T15:45:10Z INF |  https://my-test-subdomain-123.trycloudflare.com                                          |\n"
        "2026-11-07T15:45:10Z INF +--------------------------------------------------------------------------------------------+\n"
    )
    url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    match = url_regex.search(sample_log)
    assert match is not None
    assert match.group(0) == "https://my-test-subdomain-123.trycloudflare.com"


def test_cloudflare_tunnel_manager_stop_idempotent():
    """Verify calling stop() when process is None does not raise exception."""
    mgr = CloudflareTunnelManager(local_port=8000)
    mgr.stop()
    assert mgr.process is None
    assert mgr.public_url is None
