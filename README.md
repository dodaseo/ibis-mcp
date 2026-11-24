# Ibis MCP 서버

AI 에이전트가 [Ibis](https://github.com/dodaseo/ibis-releases)의 서재를 다루게 하는 MCP 서버입니다.
에이전트가 Ibis 의 검색으로 문헌을 찾고, 서재에 담고, 컬렉션으로 모읍니다. PDF 는 받지 않습니다 —
에이전트가 모아 둔 컬렉션을 Ibis 에서 열어 직접 받습니다. 받아 둔 PDF 는 따로 허용하면 에이전트가 읽습니다.

Ibis 가 켜져 있어야 동작합니다.

## 설치

쓰는 에이전트에게 이렇게 말하면 됩니다.

> https://github.com/dodaseo/ibis-mcp 의 INSTALL.md 대로 Ibis MCP 를 설치해 줘.

에이전트가 Ibis 를 찾아 등록하고, 마지막에 Ibis 의 **설정 › AI › AI 에이전트 연결**을 켜 달라고 안내합니다.
그 스위치는 직접 켭니다(서재의 서지가 에이전트 쪽으로 전달되기 시작하는 지점입니다).

직접 하려면 같은 설정 자리의 **등록 명령**을 복사해 터미널에 붙여 넣습니다. 절차는 [INSTALL.md](INSTALL.md)에 있습니다.

이 서버는 Ibis 설치본에 들어 있어(`Ibis.exe --mcp`) 따로 내려받을 것이 없습니다.

### 설치본 없이 쓰기

이 저장소의 서버를 직접 띄울 수도 있습니다(Python 3.10 이상, 다른 패키지는 필요 없습니다).

```
claude mcp add --scope user ibis -- uvx --from git+https://github.com/dodaseo/ibis-mcp ibis-mcp
```

## 도구

| 도구 | 하는 일 |
|---|---|
| `ibis_status` | 연결 상태, 서재의 문헌·컬렉션 수 |
| `ibis_sources` | 검색 소스(학술 · 법/정책 · 통계)와 검색 요령 |
| `ibis_search` | Ibis 의 키워드 찾기. `sources=["library"]` 는 내 서재만 |
| `ibis_reference` | 문헌 한 건의 상세(초록 · 주제어 · 속한 컬렉션 · PDF 보유) |
| `ibis_collections` | 컬렉션 목록 |
| `ibis_collection_create` | 컬렉션 만들기 |
| `ibis_add` | 검색 결과의 key 나 DOI 로 서재에 담기. `collection` 을 주면 그 컬렉션에도(없으면 만듦) |
| `ibis_collection_refs` | 컬렉션의 문헌과 PDF 없는 문헌 수 |
| `ibis_pdf_text` | 받아 둔 PDF 의 본문을 쪽별로(쪽 범위 지정) |
| `ibis_pdf_path` | 받아 둔 PDF 파일의 자리 — 읽기·작업 폴더로 복사는 에이전트가 직접 |
| `ibis_annotations` | PDF 에 남긴 형광펜·밑줄·메모 |

아래 셋(PDF)은 설정의 **'받아 둔 PDF 의 본문·주석도 읽습니다'**를 따로 켰을 때만 동작합니다.
지우기 · 고치기 · 설정 · AI 실행 · 원문 자동 확보는 없습니다.

## 알아 둘 것

- 검색 결과와 서지(제목 · 저자 · 초록)가 쓰는 에이전트의 제공자에게 전달됩니다. PDF 읽기를 켜면 본문과 주석도 전달됩니다.
- 연결은 이 PC 안(127.0.0.1)에서만 열리고 요청마다 토큰을 확인합니다. 설정에서 끄면 바로 닫힙니다.
- Ibis 를 업데이트하면 연결이 끊깁니다. 에이전트에서 다시 연결하면 됩니다.

## 예

> "경계선 지능 학습자의 학교 적응에 관한 국내 논문을 찾아 '경계선지능 읽기' 컬렉션에 모아 줘. 2020년 이후 것만."

에이전트가 검색어를 바꿔 가며 찾고, 고른 문헌을 컬렉션에 담은 뒤, 무엇을 담았고 PDF 가 없는 문헌이 몇 편인지 알려 줍니다.
