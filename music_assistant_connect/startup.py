"""Run Music Assistant Connect behind Home Assistant Ingress only."""
import subprocess

subprocess.run([
    "uvicorn", "main:app", "--app-dir", "/opt/ma-connect/app",
    "--host", "0.0.0.0", "--port", "8675", "--no-access-log",
], check=True)