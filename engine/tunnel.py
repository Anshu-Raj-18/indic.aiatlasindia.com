"""
AI Atlas India — Cloudflare Quick Tunnel Helper (engine/tunnel.py)
------------------------------------------------------------------
Exposes the local FastAPI Human Expert Review Portal (/review) to the web
using Cloudflare's free Quick Tunnels (trycloudflare.com).

Usage:
  python engine/tunnel.py --port 8000
  or:
  python engine/main.py --tunnel
"""

import sys
import os
import re
import shutil
import urllib.request
import subprocess
import threading
import argparse
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


def find_or_download_cloudflared() -> Optional[Path]:
    """Locate existing cloudflared binary or auto-download on Windows."""
    # 1. Check system PATH
    sys_path = shutil.which("cloudflared")
    if sys_path:
        return Path(sys_path)

    # 2. Check local repo root and home directory
    candidates = [
        REPO_ROOT / "cloudflared.exe",
        REPO_ROOT / "cloudflared",
        Path.home() / "cloudflared.exe",
        Path.home() / "cloudflared"
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            return c
        if c.exists() and sys.platform.startswith("win"):
            return c

    # 3. Auto-download for Windows if not present
    if sys.platform.startswith("win"):
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        target_path = REPO_ROOT / "cloudflared.exe"
        print(f"[Tunnel] cloudflared not found in PATH. Downloading official binary from:\n  {download_url} ...")
        try:
            urllib.request.urlretrieve(download_url, str(target_path))
            print(f"[Tunnel] Download complete: {target_path}")
            return target_path
        except Exception as e:
            print(f"[Tunnel] Auto-download failed: {e}")
            print("[Tunnel] You can manually download cloudflared from:")
            print("  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
            return None

    print("[Tunnel] cloudflared not found in PATH. Please install cloudflared:")
    print("  brew install cloudflared (macOS) or sudo apt install cloudflared (Linux)")
    return None


def run_tunnel(port: int = 8000, wait_forever: bool = True):
    """Start cloudflared tunnel and stream URL to stdout."""
    bin_path = find_or_download_cloudflared()
    if not bin_path:
        print("[Tunnel] Error: Unable to launch Cloudflare Tunnel (binary missing).")
        return None

    local_url = f"http://127.0.0.1:{port}"
    cmd = [str(bin_path), "tunnel", "--url", local_url]
    print(f"[Tunnel] Launching Cloudflare Quick Tunnel pointing to {local_url} ...")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
    except Exception as e:
        print(f"[Tunnel] Failed to start process: {e}")
        return None

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Monitor output for the trycloudflare URL
    def monitor_stream(stream):
        nonlocal tunnel_url
        for line in iter(stream.readline, ''):
            if not line:
                break
            match = url_pattern.search(line)
            if match and not tunnel_url:
                tunnel_url = match.group(0)
                print("\n" + "=" * 76)
                print(" CLOUDFLARE QUICK TUNNEL ACTIVE")
                print("=" * 76)
                print(f" Public Expert Review URL:  {tunnel_url}/review")
                print(f" Local Review Portal URL:   {local_url}/review")
                print(f" Public Analytics URL:      {tunnel_url}/analytics")
                print("=" * 76 + "\n")

    thread_err = threading.Thread(target=monitor_stream, args=(proc.stderr,), daemon=True)
    thread_out = threading.Thread(target=monitor_stream, args=(proc.stdout,), daemon=True)
    thread_err.start()
    thread_out.start()

    if wait_forever:
        try:
            proc.wait()
        except KeyboardInterrupt:
            print("\n[Tunnel] Stopping Cloudflare Tunnel...")
            proc.terminate()
            proc.wait()

    return proc


def start_tunnel_background(port: int = 8000):
    """Launch tunnel in a daemon thread so it runs alongside FastAPI server."""
    t = threading.Thread(target=run_tunnel, kwargs={"port": port, "wait_forever": True}, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Atlas India Cloudflare Quick Tunnel Helper")
    parser.add_argument("--port", type=int, default=8000, help="Local FastAPI port (default: 8000)")
    args = parser.parse_args()

    run_tunnel(port=args.port, wait_forever=True)
