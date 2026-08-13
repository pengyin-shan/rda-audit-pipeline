"""Shared HTTP (retries, rate-limit backoff), snapshot IO with retrieval timestamps (json default=str: CFF YAML dates arrive as datetime.date), CSV writing.
"""
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>\)\]\},;]+")

def http_get(url, headers=None, ok404=True, retries=3, timeout=30):
    """GET with retries. Returns Response, or None on 404 (when ok404)."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers or {}, timeout=timeout)
            if r.status_code == 404 and ok404:
                return None
            if r.status_code in (403, 429):
                wait = min(int(r.headers.get("Retry-After", "30") or 30), 120)
                print(f"  rate-limited on {url}; sleeping {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == retries - 1:
                print(f"  GIVING UP on {url}: {e}")
                return None
            time.sleep(2 ** attempt)
    return None

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def save_snapshot(cfg, project_id, surface, payload):
    """Persist a raw API result with retrieval timestamp (reproducibility + deposit)."""
    d = cfg.raw / project_id
    d.mkdir(parents=True, exist_ok=True)
    doc = {"retrieved_at": now_iso(), "surface": surface, "payload": payload}
    (d / f"{surface}.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

def load_snapshot(cfg, project_id, surface):
    p = cfg.raw / project_id / f"{surface}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")
