"""근거 기반 질의응답 데모 서버 (표준 라이브러리 http.server, 127.0.0.1에서만 열림).

실행: python -m src.demo.server [--llm] [--port 8770]  →  http://127.0.0.1:8770
  --llm  로컬 Qwen2.5-7B-Instruct로 답 문장을 생성하고 문장마다 검증한다(없으면 템플릿 답만).
화면과 응답에는 회의록 원문 인용이 들어가므로 외부에 공개하지 않는다(자기 컴퓨터에서만 연다).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent


def build(use_llm: bool):
    import torch
    from sentence_transformers import CrossEncoder, SentenceTransformer

    from src import nli
    from src.qa import IssueQA, load_llm
    llm = load_llm() if use_llm else None
    # Qwen이 GPU를 쓰면 검색용 인코더는 CPU에 둔다(8GB GPU에 다 올리지 않는다)
    dev = "cpu" if (use_llm or not torch.cuda.is_available()) else "cuda"
    kw = {"torch_dtype": torch.float16} if dev == "cuda" else {}
    enc = SentenceTransformer("BAAI/bge-m3", device=dev, model_kwargs=kw)
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", device=dev, max_length=384, model_kwargs=kw)
    return IssueQA(encoder=enc, nli=nli, reranker=rr, llm=llm)


class Handler(BaseHTTPRequestHandler):
    qa = None
    lock = Lock()

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/ask":
            qs = parse_qs(u.query)
            q = (qs.get("q") or [""])[0].strip()[:300]
            use_llm = (qs.get("llm") or ["0"])[0] == "1"
            if not q:
                return self._send(400, json.dumps({"error": "질문이 비었다"}, ensure_ascii=False))
            t = time.time()
            with self.lock:   # 모델은 한 번에 한 질문만
                a = self.qa.ask(q, use_llm=use_llm and self.qa.llm is not None)
            d = a.to_dict()
            d["seconds"] = round(time.time() - t, 1)
            d["llm_available"] = self.qa.llm is not None
            return self._send(200, json.dumps(d, ensure_ascii=False, default=str))
        if u.path == "/api/issues":
            return self._send(200, json.dumps([{"id": k, "title": c["title"], "kind": c["kind"]} for k, c in self.qa.cards.items()],
                                              ensure_ascii=False))
        return self._send(404, "{}")

    def log_message(self, *a):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--port", type=int, default=8770)
    args = ap.parse_args()
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("모델을 불러오는 중…", flush=True)
    Handler.qa = build(args.llm)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"http://127.0.0.1:{args.port} (LLM {'사용' if args.llm else '미사용'})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
