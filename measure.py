#!/usr/bin/env python3
"""
Dimensional fidelity harness for Zoo's Text-to-CAD API.

Drives every prompt in prompts/ through the API, archives the returned geometry,
and writes a run log recording prompt, request ID, status and timings.

Built against the documented Python SDK flow:
https://docs.zoo.dev/docs/developer-tools/tutorials/text-to-cad

NOTE: the underlying REST endpoint (POST /ai/text-to-cad/{output_format}) is marked
deprecated in Zoo's API reference, which recommends the /ws/ml/copilot websocket for
new integrations. This harness deliberately uses the documented path, because that is
the one a developer following the official tutorial would land on. See
findings/api-notes.md, item 5.

Usage:
    export ZOO_API_TOKEN=your_token_here
    python measure.py
"""

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from kittycad import KittyCAD, KittyCADAPIError
    from kittycad.models import FileExportFormat, TextToCad, TextToCadCreateBody
except ImportError:
    sys.exit("kittycad SDK not installed. Run: pip install -r requirements.txt")

ROOT = Path(__file__).parent
PROMPT_DIR = ROOT / "prompts"
OUTPUT_DIR = ROOT / "outputs"
POLL_SECONDS = 5
POLL_TIMEOUT = 600


def load_prompts():
    """Read prompts from prompts/*.txt, stripping the trailing NOTES section."""
    prompts = {}
    for path in sorted(PROMPT_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        # Everything before the NOTES separator is the prompt sent to the API.
        body = text.split("NOTES ON THIS PROMPT")[0]
        # Drop the title banner (first two lines) if present.
        lines = [ln for ln in body.splitlines() if set(ln.strip()) != {"="}]
        if lines and lines[0].strip().startswith("PROMPT "):
            lines = lines[1:]
        prompts[path.stem] = "\n".join(lines).strip()
    return prompts


def _poll_fn(client):
    """Resolve the polling method across SDK versions.

    The official Python tutorial teaches `get_text_to_cad_model_for_user`, but
    kittycad 1.4.0 exposes `get_text_to_cad_part_for_user`. Following the tutorial
    verbatim against the current SDK raises AttributeError. See api-notes.md item 7.
    """
    for attr in ("get_text_to_cad_part_for_user", "get_text_to_cad_model_for_user"):
        fn = getattr(client.ml, attr, None)
        if fn is not None:
            return attr, fn
    raise AttributeError(
        "No text-to-CAD polling method found on client.ml. "
        f"Available: {[a for a in dir(client.ml) if 'text_to_cad' in a]}"
    )


def generate(client, name, prompt):
    """Submit one prompt, poll to completion, write artifacts. Returns a log record."""
    record = {
        "prompt_name": name,
        "prompt": prompt,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"\n--- {name} ---")
    print(f"submitting ({len(prompt)} chars)")

    try:
        result = client.ml.create_text_to_cad(
            output_format=FileExportFormat.STEP,
            body=TextToCadCreateBody(prompt=prompt),
        )
    except KittyCADAPIError as exc:
        print(f"submit failed: {exc}")
        record["error"] = f"submit failed: {exc}"
        return record

    record["id"] = str(getattr(result, "id", ""))
    print(f"id: {record['id']}")

    poll_name, poll = _poll_fn(client)
    record["poll_method"] = poll_name

    waited = 0
    while getattr(result, "completed_at", None) is None:
        if waited >= POLL_TIMEOUT:
            record["error"] = f"timed out after {POLL_TIMEOUT}s"
            print(record["error"])
            return record
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        try:
            status_response = poll(id=result.id)
        except KittyCADAPIError as exc:
            record["error"] = f"poll failed: {exc}"
            print(record["error"])
            return record
        data = getattr(status_response, "root", status_response)
        if isinstance(data, TextToCad):
            result = data
        print(f"  polling... {waited}s  status={getattr(result, 'status', '?')}")

    record["status"] = str(getattr(result, "status", ""))
    record["completed_at"] = str(getattr(result, "completed_at", ""))
    record["elapsed_seconds"] = waited
    record["api_error"] = getattr(result, "error", None)

    # The API returns generated KCL alongside the geometry. Archive it: if the code
    # carries correct coordinates but the geometry does not, that narrows the bug.
    code = getattr(result, "code", None)
    if code:
        code_path = OUTPUT_DIR / f"{name}.kcl"
        code_path.write_text(code, encoding="utf-8")
        record["code_file"] = code_path.name
        print(f"  wrote {code_path.name}")

    written = []
    outputs = getattr(result, "outputs", None) or {}
    for filename, b64 in dict(outputs).items():
        target = OUTPUT_DIR / f"{name}__{filename}"
        target.write_bytes(base64.b64decode(b64))
        written.append(target.name)
        print(f"  wrote {target.name}")
    record["files"] = written

    if not written:
        print("  no geometry returned")

    return record


def main():
    if not os.environ.get("ZOO_API_TOKEN"):
        sys.exit("ZOO_API_TOKEN is not set. Export it and try again.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    prompts = load_prompts()
    if not prompts:
        sys.exit(f"No prompts found in {PROMPT_DIR}")

    print(f"Zoo Text-to-CAD fidelity harness — {len(prompts)} prompt(s)")
    client = KittyCAD()

    log = {
        "run_started": datetime.now(timezone.utc).isoformat(),
        "output_format": "step",
        "runs": [generate(client, name, text) for name, text in prompts.items()],
    }

    log_path = OUTPUT_DIR / "run_log.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\nRun log written to {log_path}")
    print("Measurement is manual: open the STEP files and compare against the")
    print("constraints in each prompt. See README for the results table.")


if __name__ == "__main__":
    main()
