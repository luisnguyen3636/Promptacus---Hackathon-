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
        local_port: int = 8000,
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
        if not os.path.isfile(self.bin_path) or not os.access(self.bin_path, os.X_OK):
            logger.warning(f"cloudflared binary not found at '{self.bin_path}'. Tunnel cannot start.")
            return None

        cmd = [
            self.bin_path,
            "tunnel",
            "--edge-ip-version", "4",
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

            # Wait for public URL
            got_url = self._url_event.wait(timeout=timeout_seconds)
            if got_url and self.public_url:
                logger.info(f"Cloudflare Tunnel active: {self.public_url}")
                return self.public_url
            else:
                logger.warning(f"Tunnel did not output public URL within {timeout_seconds}s.")
                return None
        except Exception as e:
            logger.error(f"Failed to start cloudflared tunnel: {e}")
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
                    self._url_event.set()
        except Exception:
            pass
        finally:
            self._url_event.set()

    def stop(self) -> None:
        """Gracefully terminate cloudflared subprocess."""
        self._stopped = True
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
            except Exception:
                pass
            finally:
                self.process = None
                self.public_url = None
