#!/usr/bin/env python3
"""Validate Woo Creator block-validation manifest targets through Studio MCP."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _bundle_paths import resolve_bundle_dir


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MANIFEST_DIRNAME = ".block-validation"
MCP_PROTOCOL_VERSION = "2024-11-05"


class StudioMcpClient:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            ["studio", "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._next_id = 1
        self._initialize()

    def _request(self, method: str, params: dict | None = None) -> dict:
        if self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("studio mcp stdio is unavailable")

        req_id = self._next_id
        self._next_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

        while True:
            line = self.proc.stdout.readline()
            if line == "":
                stderr = ""
                if self.proc.stderr is not None:
                    stderr = self.proc.stderr.read().strip()
                raise RuntimeError(f"studio mcp closed unexpectedly. {stderr}".strip())
            line = line.strip()
            if not line:
                continue
            message = json.loads(line)
            if message.get("id") != req_id:
                continue
            if "error" in message:
                raise RuntimeError(f"studio mcp {method} failed: {message['error']}")
            return message["result"]

    def _initialize(self) -> None:
        result = self._request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "woo-creator-block-validator",
                    "version": "0.1.0",
                },
            },
        )
        protocol = result.get("protocolVersion")
        if protocol != MCP_PROTOCOL_VERSION:
            raise RuntimeError(
                f"Unexpected Studio MCP protocol version {protocol!r}; expected {MCP_PROTOCOL_VERSION!r}"
            )

    def validate_blocks(self, *, site_path: str, file_path: str) -> str:
        result = self._request(
            "tools/call",
            {
                "name": "validate_blocks",
                "arguments": {
                    "nameOrPath": site_path,
                    "filePath": file_path,
                },
            },
        )
        content = result.get("content") or []
        text_chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    text_chunks.append(text)
        return "\n".join(chunk for chunk in text_chunks if chunk).strip()

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "blueprint_dir",
        help="Blueprint bundle directory or slug. Bare names resolve under <repo>/blueprints/<slug>-blueprint/.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Explicit manifest path. Defaults to <bundle>/.block-validation/manifest.json.",
    )
    parser.add_argument(
        "--site-path",
        default=None,
        help="Override Studio site path. Defaults to manifest site_path, then <bundle>/.studio-site.",
    )
    parser.add_argument(
        "--label",
        action="append",
        dest="labels",
        default=None,
        help="Validate only selected manifest labels. Repeat to validate more than one target.",
    )
    parser.add_argument(
        "--stop-on-first-failure",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Stop after the first invalid target.",
    )
    return parser.parse_args()


def load_manifest(bundle_dir: Path, manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Manifest JSON is invalid: {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise SystemExit(f"Manifest must be a JSON object: {manifest_path}")
    bundle_value = manifest.get("bundle_dir")
    if isinstance(bundle_value, str) and Path(bundle_value).resolve() != bundle_dir.resolve():
        print(
            f"note: manifest bundle_dir {bundle_value} does not match resolved bundle {bundle_dir}",
            file=sys.stderr,
        )
    return manifest


def select_targets(manifest: dict, labels: list[str] | None) -> list[dict]:
    raw_targets = manifest.get("targets")
    if not isinstance(raw_targets, list):
        raise SystemExit("Manifest is missing targets[]")

    targets = [target for target in raw_targets if isinstance(target, dict)]
    if labels:
        wanted = set(labels)
        targets = [target for target in targets if target.get("label") in wanted]
    return targets


def is_invalid(report: str) -> bool:
    return (
        "Invalid blocks:" in report
        or report.startswith("Block validation failed:")
        or "Block validation error:" in report
    )


def main() -> int:
    args = parse_args()
    bundle_dir = resolve_bundle_dir(args.blueprint_dir)
    if not bundle_dir.is_dir():
        raise SystemExit(f"Blueprint bundle directory not found: {bundle_dir}")

    manifest_path = (
        Path(args.manifest).expanduser().resolve()
        if args.manifest
        else (bundle_dir / DEFAULT_MANIFEST_DIRNAME / "manifest.json").resolve()
    )
    manifest = load_manifest(bundle_dir, manifest_path)
    site_path = args.site_path or manifest.get("site_path") or str(bundle_dir / ".studio-site")
    if not isinstance(site_path, str) or not site_path.strip():
        raise SystemExit("Studio site path is missing. Pass --site-path or regenerate the manifest with one.")
    site_path = str(Path(site_path).expanduser().resolve())

    targets = select_targets(manifest, args.labels)
    if not targets:
        print("No validation targets selected.")
        return 0

    failures: list[tuple[dict, str]] = []
    client = StudioMcpClient()
    try:
        for index, target in enumerate(targets, start=1):
            validate_file = target.get("validate_file")
            label = target.get("label") or target.get("source_path") or f"target-{index}"
            if not isinstance(validate_file, str):
                failures.append((target, "Manifest target is missing validate_file"))
                if args.stop_on_first_failure:
                    break
                continue
            report = client.validate_blocks(site_path=site_path, file_path=validate_file)
            first_line = report.splitlines()[0] if report else "No report returned"
            print(f"[{index}/{len(targets)}] {label}: {first_line}")
            if is_invalid(report):
                failures.append((target, report))
                if args.stop_on_first_failure:
                    break
    finally:
        client.close()

    if failures:
        print("", file=sys.stderr)
        print(f"{len(failures)} validation target(s) failed.", file=sys.stderr)
        for target, report in failures:
            label = target.get("label") or target.get("source_path") or "<unknown>"
            source_path = target.get("source_path") or "<unknown>"
            validate_file = target.get("validate_file") or "<unknown>"
            print("", file=sys.stderr)
            print(f"Label: {label}", file=sys.stderr)
            print(f"Source: {source_path}", file=sys.stderr)
            print(f"Validate file: {validate_file}", file=sys.stderr)
            print(report.rstrip(), file=sys.stderr)
        return 1

    print(f"All {len(targets)} validation target(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
