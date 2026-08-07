#!/usr/bin/env python3
"""Run a bounded local real-Prometheus bearer-auth scrape rehearsal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/fixtures/memory-os-operability/local-prometheus-process-rehearsal-results.v1.json"
PROM_IMAGE = "prom/prometheus:v3.5.0"
FIXTURE_METRIC = "memory_os_local_prometheus_fixture_total"
JOB = "memory_os_local_fixture"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr[-1000:]}")
    return completed.stdout.strip()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def get_json(url: str, timeout: float = 2.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    require(isinstance(value, dict), f"non-object JSON from {url}")
    return value


def wait_http_ok(url: str, deadline: float) -> None:
    last = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # bounded readiness polling
            last = str(exc)
        time.sleep(0.25)
    raise Fail(f"timed out waiting for {url}: {last}")


def query_scalar(base_url: str, expression: str, deadline: float) -> float:
    encoded = urllib.parse.urlencode({"query": expression})
    last = ""
    while time.time() < deadline:
        try:
            value = get_json(f"{base_url}/api/v1/query?{encoded}")
            if value.get("status") != "success":
                raise ValueError(f"query status={value.get('status')!r}")
            data = value.get("data")
            if not isinstance(data, dict):
                raise ValueError("query data missing")
            rows = data.get("result")
            if isinstance(rows, list) and rows:
                sample = rows[0]
                if isinstance(sample, dict):
                    pair = sample.get("value")
                    if isinstance(pair, list) and len(pair) == 2:
                        return float(pair[1])
        except Exception as exc:
            last = str(exc)
        time.sleep(0.5)
    raise Fail(f"timed out querying {expression!r}: {last}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(str(output).startswith(str(ROOT.resolve())), "output must remain inside repository")
    require(subprocess.run(["docker", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0,
            "docker is required for the local Prometheus process rehearsal")

    source_sha = git("rev-parse", "HEAD")
    require(len(source_sha) == 40, "source commit must be full SHA")
    token = secrets.token_urlsafe(32)
    token_digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    fixture_port = free_port()
    prometheus_port = free_port()
    counters = {"authorizedScrapes": 0, "unauthorizedRequests": 0}
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "MemoryOSMetricsFixture/1"
        sys_version = ""

        def log_message(self, format: str, *values: object) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/metrics":
                self.send_response(404)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            if self.headers.get("Authorization", "") != f"Bearer {token}":
                with lock:
                    counters["unauthorizedRequests"] += 1
                self.send_response(401)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"unauthorized\n")
                return
            with lock:
                counters["authorizedScrapes"] += 1
            body = (
                "# HELP memory_os_local_prometheus_fixture_total Local synthetic Prometheus process rehearsal fixture.\n"
                "# TYPE memory_os_local_prometheus_fixture_total counter\n"
                "memory_os_local_prometheus_fixture_total 1\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", fixture_port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    unauthorized_rejected = False
    container_name = f"memory-os-prometheus-rehearsal-{os.getpid()}"
    process: subprocess.Popen[str] | None = None
    image_id = ""
    try:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{fixture_port}/metrics", timeout=2.0)
        except urllib.error.HTTPError as exc:
            unauthorized_rejected = exc.code == 401
        require(unauthorized_rejected, "fixture did not reject unauthenticated scrape")

        with tempfile.TemporaryDirectory(prefix="memory-os-prometheus-") as temp_dir:
            temp = Path(temp_dir)
            os.chmod(temp, 0o755)
            token_path = temp / "metrics-token"
            config_path = temp / "prometheus.yml"
            token_path.write_text(token + "\n", encoding="utf-8")
            token_path.chmod(0o444)
            config_path.write_text(
                "global:\n"
                "  scrape_interval: 1s\n"
                "  scrape_timeout: 1s\n"
                "scrape_configs:\n"
                f"  - job_name: {JOB}\n"
                "    metrics_path: /metrics\n"
                "    authorization:\n"
                "      type: Bearer\n"
                "      credentials_file: /run/secrets/metrics-token\n"
                "    static_configs:\n"
                f"      - targets: ['127.0.0.1:{fixture_port}']\n",
                encoding="utf-8",
            )
            config_path.chmod(0o444)

            command = [
                "docker", "run", "--rm", "--name", container_name, "--network", "host",
                "-v", f"{config_path}:/etc/prometheus/prometheus.yml:ro",
                "-v", f"{token_path}:/run/secrets/metrics-token:ro",
                PROM_IMAGE,
                "--config.file=/etc/prometheus/prometheus.yml",
                f"--web.listen-address=127.0.0.1:{prometheus_port}",
                "--storage.tsdb.path=/prometheus",
                "--storage.tsdb.retention.time=30m",
                "--log.level=warn",
            ]
            process = subprocess.Popen(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            deadline = time.time() + 90
            wait_http_ok(f"http://127.0.0.1:{prometheus_port}/-/ready", deadline)
            up_value = query_scalar(
                f"http://127.0.0.1:{prometheus_port}",
                f'up{{job="{JOB}"}}',
                deadline,
            )
            metric_value = query_scalar(
                f"http://127.0.0.1:{prometheus_port}",
                FIXTURE_METRIC,
                deadline,
            )
            require(up_value == 1.0, f"Prometheus target up value was {up_value}")
            require(metric_value == 1.0, f"fixture metric value was {metric_value}")
            with lock:
                authorized_scrapes = int(counters["authorizedScrapes"])
                unauthorized_requests = int(counters["unauthorizedRequests"])
            require(authorized_scrapes >= 1, "Prometheus never reached the authorized fixture path")
            require(unauthorized_requests >= 1, "unauthorized request probe was not recorded")

            inspect = subprocess.run(
                ["docker", "image", "inspect", PROM_IMAGE, "--format", "{{.Id}}"],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            require(inspect.returncode == 0, f"cannot inspect Prometheus image: {inspect.stderr[-1000:]}")
            image_id = inspect.stdout.strip()
            require(image_id.startswith("sha256:") and len(image_id) == 71, "Prometheus image ID is not sha256")

        result = {
            "schemaVersion": "memory-os-local-prometheus-process-rehearsal-results.v1",
            "sourceCommitSha": source_sha,
            "classification": "LOCAL_REAL_PROMETHEUS_PROCESS_REHEARSAL",
            "dependencyMode": "LOOPBACK_SYNTHETIC_AUTH_FIXTURE_PLUS_PROMETHEUS_DOCKER",
            "prometheusImage": PROM_IMAGE,
            "prometheusImageId": image_id,
            "assertions": {
                "realPrometheusProcessStarted": True,
                "bearerTokenFileConfigured": True,
                "unauthorizedFixtureRequestRejected": True,
                "prometheusTargetUp": True,
                "fixtureMetricIngestedAndQueryable": True,
                "fixtureTokenAbsentFromResult": True,
                "canonicalGoHandlerUsedByExternalProcess": False,
                "productionMetricsBackendUsed": False,
                "productionNetworkPolicyExercised": False,
                "productionCredentialsUsed": False,
                "productionTrafficUsed": False,
            },
            "observations": {
                "authorizedScrapeCountAtVerification": authorized_scrapes,
                "unauthorizedProbeCount": unauthorized_requests,
                "targetUpValue": up_value,
                "fixtureMetricValue": metric_value,
                "tokenSha256Persisted": False,
            },
            "result": "PASS",
            "productionEvidence": False,
            "productionMetricsBackendEvidence": False,
            "canonicalHandlerExternalScrapeEvidence": False,
            "productionReady": False,
            "limitations": [
                "the scraped endpoint is a strict synthetic loopback fixture, not the canonical Go metrics handler",
                "canonical Go scrape-handler authentication, redaction and output behavior remain covered by separate repository tests and validators",
                "Prometheus runs in one local Docker container with host networking and no production network policy",
                "the bearer token is generated ephemerally and is not production secret provisioning",
                "no remote metrics backend, retention deletion, dashboard deployment, paging route, production traffic or production credentials are exercised"
            ],
        }
        serialized = json.dumps(result, indent=2) + "\n"
        require(token not in serialized and token_digest not in serialized, "ephemeral bearer material leaked into result")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
        print("Memory OS local real-Prometheus process rehearsal PASS")
        print(f"source commit: {source_sha}")
        print(f"Prometheus image ID: {image_id}")
        print(f"authorized scrapes observed: {authorized_scrapes}")
        print("production metrics backend evidence: false")
        print("canonical external handler evidence: false")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        if process is not None:
            subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL PROMETHEUS PROCESS REHEARSAL FAILED: {exc}")
        raise SystemExit(1)
