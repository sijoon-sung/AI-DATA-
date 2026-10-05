"""정답셋 검수 도구 서버 (표준 라이브러리만 사용, 127.0.0.1에서만 열림).

실행: uv run python -m src.labeler.server  →  http://127.0.0.1:8765
  표본: data/labels/pool_{task}.jsonl  (scripts/06_label_pool.py가 만든다)
  결과: data/labels/gold_{task}.jsonl  (한 줄 = 라벨 하나, 같은 pid는 마지막 줄이 유효)
규칙 라벨(weak)은 검수자에게 보내지 않는다. 미리 보면 판단이 그쪽으로 끌리기 때문이다.
"""
from __future__ import annotations

import json
import math
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "data" / "labels"
HERE = Path(__file__).resolve().parent
TASKS = ["ref", "proc", "topdown"]


def load_pool(task):
    path = LABELS / f"pool_{task}.jsonl"
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if isinstance(d.get("weak"), float) and math.isnan(d["weak"]):
            d["weak"] = None
        items.append(d)
    return items


POOLS = {t: load_pool(t) for t in TASKS}


def load_gold(task):
    path = LABELS / f"gold_{task}.jsonl"
    gold = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                if d.get("label") == "__UNDO__":
                    gold.pop(d["pid"], None)
                else:
                    gold[d["pid"]] = d
    return gold


def append_gold(task, rec):
    with open(LABELS / f"gold_{task}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def public(item):
    return {k: v for k, v in item.items() if k != "weak"}


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # 콘솔 로그 생략
        pass

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/stats":
            out = {}
            for t in TASKS:
                g = load_gold(t)
                counts = {}
                for d in g.values():
                    counts[d["label"]] = counts.get(d["label"], 0) + 1
                out[t] = {"total": len(POOLS[t]), "done": len(g), "counts": counts}
            self._json(out)
        elif u.path == "/api/next":
            t = q.get("task", "ref")
            g = load_gold(t)
            nxt = next((it for it in POOLS[t] if it["pid"] not in g), None)
            self._json({"item": public(nxt) if nxt else None, "done": len(g), "total": len(POOLS[t])})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or b"{}")
        t = data.get("task")
        if t not in TASKS:
            return self._json({"error": "bad task"}, 400)
        if u.path == "/api/label":
            append_gold(t, {"pid": data["pid"], "label": data["label"], "note": data.get("note", ""),
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
            self._json({"ok": True})
        elif u.path == "/api/undo":
            g = load_gold(t)
            if g:
                last = max(g.values(), key=lambda d: d["ts"])
                append_gold(t, {"pid": last["pid"], "label": "__UNDO__", "ts": time.strftime("%Y-%m-%dT%H:%M:%S")})
                self._json({"ok": True, "pid": last["pid"]})
            else:
                self._json({"ok": False})
        else:
            self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    LABELS.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("검수 도구: http://127.0.0.1:8765", {t: len(p) for t, p in POOLS.items()}, flush=True)
    srv.serve_forever()
