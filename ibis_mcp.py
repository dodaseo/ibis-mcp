"""Ibis MCP 서버 — AI 에이전트가 **켜져 있는 Ibis** 로 검색하고, 서지를 서재에 담고, 컬렉션으로 모은다.

표준입출력 MCP 서버(줄마다 JSON-RPC 하나). Ibis 의 '에이전트 연결'(설정 › AI)에 요청을 옮기는 얇은 껍데기다.
PDF 는 받지 않는다(사용자가 Ibis 에서 직접). 표준 라이브러리만 쓴다.

Ibis 설치본에는 같은 서버가 들어 있다(`Ibis.exe --mcp`). 이 파일은 그것과 같은 내용이다.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PROTOCOL = 1                                  # 다리(agent_bridge.PROTOCOL)와 맞아야 한다
MCP_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
STOP_MARK = "agent-mcp-stop"                  # 앱 폴더에 생기면 끝낸다(이 프로세스가 뜬 뒤에 생긴 것만)
SERVER_VERSION = "1.0.0"

INSTRUCTIONS = (
    "Ibis(서지 관리 앱)의 서재를 다룬다. 흐름: ibis_sources 로 소스·검색 요령 확인 → ibis_search 를 짧은 검색어로 여러 번 → "
    "쓸 문헌의 key 를 ibis_add 로 담으면서 collection 이름을 주어 한 컬렉션에 모은다 → ibis_collection_refs 로 모은 것과 "
    "PDF 없는 문헌을 확인해 사용자에게 알린다. PDF 는 사용자가 Ibis 에서 직접 받는다. 서지를 지어내지 말 것 — "
    "검색 결과에 없는 문헌은 DOI 로만 담는다. 지우거나 고치는 도구는 없다. 사용자가 받아 둔 PDF 는 ibis_pdf_text(본문) · "
    "ibis_annotations(형광펜·메모) · ibis_pdf_path(파일 자리)로 읽는다 — 사용자가 그 스위치를 켠 경우에만."
)

_S = {"type": "string"}
_I = {"type": "integer"}
_L = {"type": "array", "items": {"type": "string"}}


def _tool(name, op, desc, props=None, required=()):
    return {"name": name, "op": op, "description": desc,
            "inputSchema": {"type": "object", "properties": props or {}, "required": list(required),
                            "additionalProperties": False}}


TOOLS = (
    _tool("ibis_status", "status", "Ibis 연결 상태 — 앱 버전, 서재의 문헌 수·컬렉션 수."),
    _tool("ibis_sources", "sources", "검색 소스 목록(학술·법/정책·통계 범위별)과 Ibis 의 검색 요령. 검색 전에 한 번 읽는다."),
    _tool("ibis_search", "search",
          "Ibis 의 키워드 찾기로 검색한다(앱 화면의 검색과 같은 경로). query 는 짧게 — 핵심 개념 1~2개. 국문 DB 는 제목에 "
          "걸리므로 긴 문장은 0건이 된다(개념을 바꿔 여러 번 검색). sources 예: [\"kci\"] · [\"kci\",\"scienceon\",\"nl_seoji\"] · "
          "[\"openalex\",\"crossref\"] · [\"library\"](내 서재만). 학술·법/정책·통계 범위는 한 번에 섞지 않는다. 생략하면 "
          "[\"kci\"]. 결과의 more 가 참이면 다음 page 가 있다. rows 의 key 를 ibis_add 에 넘겨 담는다.",
          {"query": _S, "sources": _L, "page": _I, "year_from": _I, "year_to": _I}, ("query",)),
    _tool("ibis_reference", "reference",
          "문헌 한 건의 상세 — 서지 칸, 초록, 주제어, 속한 컬렉션, PDF 보유 여부. key 는 검색 결과나 서재의 것.",
          {"key": _S}, ("key",)),
    _tool("ibis_collections", "collections", "서재의 컬렉션 목록(id·이름·상위·문헌 수)."),
    _tool("ibis_collection_create", "collection_create",
          "컬렉션을 만든다(같은 이름이 있으면 그것을 돌려준다). parent 는 상위 컬렉션의 이름이나 id(선택).",
          {"name": _S, "parent": _S}, ("name",)),
    _tool("ibis_add", "add",
          "문헌을 서재에 담는다. collection(이름 또는 id)을 주면 그 컬렉션에도 넣는다 — 없으면 만든다. keys: ibis_search "
          "결과의 key 목록(이미 서재에 있는 문헌도 된다 — 컬렉션에만 넣는다). dois: 검색 결과에 없는 문헌은 DOI 로(Ibis 가 "
          "등록기관에서 서지를 가져온다). 반환: added · already_in_library · in_collection · failed(사유).",
          {"keys": _L, "dois": _L, "collection": _S}),
    _tool("ibis_collection_refs", "collection_refs",
          "컬렉션에 담긴 문헌 목록 — 문헌마다 has_pdf, 그리고 PDF 없는 문헌 수(missing_pdf). 사용자에게 받을 PDF 를 알릴 때 쓴다.",
          {"collection": _S}, ("collection",)),
    _tool("ibis_pdf_text", "pdf_text",
          "서재 문헌에 붙은 PDF 의 본문을 쪽별로 읽는다(has_pdf 가 참인 문헌만 — 사용자가 Ibis 에서 받아 둔 파일). "
          "page_from·page_to 로 쪽 범위를 정한다(생략하면 전부 — 긴 문서는 pages_total 을 먼저 보고 나눠 읽는다). "
          "첨부가 여럿이면 file 에 파일 이름. 사용자가 'PDF 본문·주석 읽기'를 켜 둬야 한다(ibis_status 의 pdf_reading).",
          {"key": _S, "page_from": _I, "page_to": _I, "file": _S}, ("key",)),
    _tool("ibis_pdf_path", "pdf_path",
          "서재 문헌에 붙은 PDF 파일의 자리(전체 경로·크기). 표·그림까지 봐야 하거나 작업 폴더에 사본을 둘 때 — 읽기·복사는 "
          "에이전트가 제 도구로 한다(원본을 옮기거나 고치지 말 것).",
          {"key": _S}, ("key",)),
    _tool("ibis_annotations", "annotations",
          "사용자가 그 문헌의 PDF 에 남긴 형광펜·밑줄·메모(쪽·종류·칠한 문장·메모). 사용자가 무엇을 중요하게 봤는지 알 때 쓴다.",
          {"key": _S}, ("key",)),
    _tool("ibis_annotate", "annotate",
          "서재 문헌의 PDF 에 형광펜·밑줄·메모를 남긴다. items 의 각 항목: type(highlight|underline|note) · page(ibis_pdf_text "
          "의 page) · text(칠할 문장 — 그 쪽 본문에서 **글자 그대로** 옮긴다, 8자 이상. note 는 생략 가능 = 쪽 메모) · "
          "note(메모 글 — note 는 필수, 형광펜·밑줄에는 선택). model 에는 지금 답하는 모델의 이름을 적는다(주석 하단에 "
          "표기된다 — 예: 'Claude Opus 5.5'). 자리는 사용자가 그 PDF 를 열 때 정해진다. 사용자가 'PDF 에 주석 남기기'를 "
          "켜 둬야 한다(ibis_status 의 annotating). 사용자가 요청한 만큼만 남긴다 — 문서를 주석으로 덮지 말 것.",
          {"key": _S, "model": _S, "file": _S,
           "items": {"type": "array", "items": {"type": "object", "properties": {
               "type": {"type": "string", "enum": ["highlight", "underline", "note"]}, "page": _I, "text": _S,
               "note": _S}, "required": ["type", "page"]}}},
          ("key", "model", "items")),
)
_BY_NAME = {t["name"]: t for t in TOOLS}


def app_dir() -> Path:
    return Path(os.environ.get("IBIS_APP_DIR") or (Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Ibis"))


def call_bridge(op: str, args: dict) -> dict:
    try:
        ep = json.loads((app_dir() / "agent-endpoint.json").read_text(encoding="utf-8"))
        port, token = int(ep["port"]), str(ep["token"])
    except (OSError, ValueError, KeyError):
        return {"ok": False, "error": "Ibis 에 연결할 수 없습니다 — Ibis 가 켜져 있는지, 설정 › AI 의 'AI 에이전트 연결'을 "
                                      "켰는지 확인하세요."}
    body = json.dumps({"protocol": PROTOCOL, "op": op,
                       "args": {k: v for k, v in args.items() if v not in (None, "", [])}},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/agent", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                                          "Host": f"127.0.0.1:{port}"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))      # 로컬 호출은 프록시를 타지 않는다
    try:
        with opener.open(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            return {"ok": False, "error": f"Ibis 응답 오류({e.code})"}
    except OSError:
        return {"ok": False, "error": "Ibis 가 응답하지 않습니다 — 앱이 꺼졌으면 다시 켜세요"}


def handle(msg: dict):
    """요청 하나 → 응답 dict(알림이면 None)."""
    mid, method = msg.get("id"), msg.get("method")
    if not isinstance(method, str) or "id" not in msg:
        return None                                     # 알림(notifications/initialized 등)에는 답하지 않는다
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    if method == "initialize":
        want = params.get("protocolVersion")
        return ok({"protocolVersion": want if want in MCP_VERSIONS else MCP_VERSIONS[0],
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "ibis", "version": SERVER_VERSION}, "instructions": INSTRUCTIONS})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [{k: t[k] for k in ("name", "description", "inputSchema")} for t in TOOLS]})
    if method == "tools/call":
        tool = _BY_NAME.get(params.get("name"))
        args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if tool is None:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "모르는 도구"}}
        allowed = tool["inputSchema"]["properties"]
        out = call_bridge(tool["op"], {k: v for k, v in args.items() if k in allowed})
        return ok({"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}],
                   "isError": not out.get("ok", False)})
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "지원하지 않는 메서드"}}


def _streams():
    """표준입출력을 바이트로 — 창 전용 실행 파일(Ibis.exe)은 sys.stdin/stdout 이 None 일 수 있어 fd 로 다시 연다."""
    def grab(stream, fd, mode):
        if stream is not None and getattr(stream, "buffer", None) is not None:
            return stream.buffer
        return os.fdopen(fd, mode, buffering=0)
    return grab(sys.stdin, 0, "rb"), grab(sys.stdout, 1, "wb")


def _watch_stop(started: float) -> None:
    mark = app_dir() / STOP_MARK
    while True:
        time.sleep(1.0)
        try:
            if mark.stat().st_mtime >= started - 1:
                os._exit(0)                            # 설치 폴더의 실행 파일을 놓아 준다(업데이트가 기다린다)
        except OSError:
            pass


def main() -> int:
    try:
        rd, wr = _streams()
    except OSError:
        return 2
    threading.Thread(target=_watch_stop, args=(time.time(),), daemon=True).start()
    lock = threading.Lock()
    for raw in iter(rd.readline, b""):
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON 이 아닙니다"}}
        else:
            if not isinstance(msg, dict):
                reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "잘못된 요청"}}
            else:
                try:
                    reply = handle(msg)
                except Exception:  # noqa: BLE001 — 요청 하나의 실패가 서버를 죽이지 않는다
                    reply = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32603, "message": "내부 오류"}}
        if reply is not None:
            try:
                with lock:
                    wr.write(json.dumps(reply, ensure_ascii=False).encode("utf-8") + b"\n")
                    wr.flush()
            except OSError:
                # 표준출력이 이어져 있지 않다 — 창 전용 실행 파일을 PowerShell 의 `'…' | & Ibis.exe --mcp` 로 부르면 그렇다
                # (실측 2026-11-24: bash·cmd 파이프·Start-Process 재지정·에이전트의 파이프는 된다). 조용히 끝낸다.
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
