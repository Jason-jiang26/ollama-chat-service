"""Exercise a running API and real model: python scripts/smoke_test.py."""
import argparse
import json
import sys
import time

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--message", default="你好，请用一句中文介绍自己。")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=130, trust_env=False) as client:
        for path in ("/health", "/ready"):
            response = client.get(path)
            print(f"GET {path}: HTTP {response.status_code}")
            response.raise_for_status()
        start = time.perf_counter()
        response = client.post("/chat", json={"message": args.message})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("reply"), str) or not payload["reply"].strip():
            raise RuntimeError("The model did not return a nonempty text reply")
        print(json.dumps({
            "request": args.message,
            "response": payload,
            "elapsed_seconds": round(time.perf_counter() - start, 3),
        }, ensure_ascii=False, indent=2))
    print("PASS: real Ollama request completed (answer quality is not evaluated).")


if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
