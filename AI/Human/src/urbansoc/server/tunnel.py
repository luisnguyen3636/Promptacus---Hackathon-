"""Native Python Cloudflare Tunnel Manager for Urban Safety AI-SOC."""

import atexit
import logging
import os
import re
import signal
import subprocess
import threading
import time
from typing import Optional

logger = logging.getLogger("urbansoc.server.tunnel")


class CloudflareTunnelManager:
    """Manages the lifecycle of an account-less Cloudflare Quick Tunnel subprocess."""

    def __init__(
        self,
        local_port: int = 7777,
        local_host: str = "127.0.0.1",
        bin_path: Optional[str] = None,
    ) -> None:
        self.local_port = local_port
        self.local_host = local_host
        self.bin_path = bin_path or self._resolve_bin_path()
        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self._url_event = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        self._stopped = False

        atexit.register(self.stop)

    def _persist_url(self, url: str) -> None:
        """Save discovered public URL to disk for easy retrieval by scripts and users."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        for path in [
            "/tmp/soc_public_url.txt",
            os.path.join(project_root, "latest_tunnel_url.txt"),
        ]:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(url.strip() + "\n")
            except Exception:
                pass

    def _resolve_bin_path(self) -> str:
        """Find cloudflared binary in project bin/ or system PATH."""
        # Check relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        local_bin = os.path.join(project_root, "bin", "cloudflared")
        if os.path.isfile(local_bin) and os.access(local_bin, os.X_OK):
            return local_bin

        # Check system PATH
        import shutil
        sys_bin = shutil.which("cloudflared")
        if sys_bin:
            return sys_bin

        return local_bin

    def start(self, timeout_seconds: float = 15.0) -> Optional[str]:
        """Start the tunnel subprocess and wait for the public URL to be assigned."""
        # 1. Try Cloudflare Quick Tunnel first
        if os.path.isfile(self.bin_path) and os.access(self.bin_path, os.X_OK):
            cmd = [
                self.bin_path,
                "tunnel",
                "--url", f"http://{self.local_host}:{self.local_port}",
                "--no-autoupdate",
            ]
            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                self._reader_thread = threading.Thread(
                    target=self._monitor_output,
                    name="CloudflareTunnelReader",
                    daemon=True,
                )
                self._reader_thread.start()

                # Wait for Cloudflare URL or early exit
                got_url = self._url_event.wait(timeout=4.5)
                if got_url and self.public_url:
                    logger.info(f"Cloudflare Tunnel active: {self.public_url}")
                    return self.public_url
                else:
                    logger.warning("Cloudflare quick tunnel unavailable or rate-limited (429). Activating resilient HTTPS TLS tunnel fallback...")
                    self._stop_process()
            except Exception as e:
                logger.warning(f"Cloudflare tunnel init error: {e}")
                self._stop_process()

        # 2. Resilient HTTPS TLS Reverse Tunnel Fallback (Zero rate limit, full HTTPS/HLS support)
        return self._start_fallback_tunnel(timeout_seconds=min(10.0, timeout_seconds))

    def _start_fallback_tunnel(self, timeout_seconds: float = 8.0) -> Optional[str]:
        """Start SSH-based HTTPS TLS tunnel fallback with automatic TLS termination."""
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ServerAliveInterval=30",
            "-o", "LogLevel=ERROR",
            "-R", f"80:localhost:{self.local_port}",
            "nokey@localhost.run",
        ]
        try:
            self._url_event.clear()
            self._stopped = False
            self.public_url = None
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._reader_thread = threading.Thread(
                target=self._monitor_fallback_output,
                name="SshHttpsTunnelReader",
                daemon=True,
            )
            self._reader_thread.start()

            got_url = self._url_event.wait(timeout=timeout_seconds)
            if got_url and self.public_url:
                logger.info(f"Resilient HTTPS Tunnel active: {self.public_url}")
                return self.public_url
            else:
                logger.warning(f"Fallback tunnel did not assign public URL within {timeout_seconds}s.")
                return None
        except Exception as e:
            logger.error(f"Failed to start fallback HTTPS tunnel: {e}")
            return None

    def _monitor_output(self) -> None:
        """Monitor stdout of cloudflared process to extract trycloudflare.com URL."""
        url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
        if not self.process or not self.process.stdout:
            return

        try:
            for line in iter(self.process.stdout.readline, ""):
                if self._stopped:
                    break
                match = url_regex.search(line)
                if match and not self.public_url:
                    self.public_url = match.group(0)
                    self._persist_url(self.public_url)
                    self._url_event.set()
                    break
                if "provisioning failed" in line or "429" in line:
                    logger.warning("Cloudflare tunnel: %s", line.strip())
                    self._url_event.set()
                    break
        except Exception:
            pass
        finally:
            self._url_event.set()

    def _monitor_fallback_output(self) -> None:
        """Monitor stdout of SSH fallback tunnel to extract https://*.lhr.life URL."""
        url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.lhr\.life")
        if not self.process or not self.process.stdout:
            return

        try:
            for line in iter(self.process.stdout.readline, ""):
                if self._stopped:
                    break
                match = url_regex.search(line)
                if match and not self.public_url:
                    self.public_url = match.group(0)
                    self._persist_url(self.public_url)
                    self._url_event.set()
                    break
        except Exception:
            pass
        finally:
            self._url_event.set()

    def _stop_process(self) -> None:
        """Helper to terminate current tunnel process."""
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=1.5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
            except Exception:
                pass
            finally:
                self.process = None

    def stop(self) -> None:
        """Gracefully terminate tunnel subprocess."""
        self._stopped = True
        self._stop_process()
        self.public_url = None
