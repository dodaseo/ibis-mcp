# Ibis MCP 설치 절차 (에이전트용)

이 문서는 AI 에이전트가 읽고 그대로 수행하도록 쓴 절차입니다. 사용자가 "Ibis MCP 를 설치해 줘"라고 하면 아래 순서대로 합니다.
Windows 기준입니다.

## 1. Ibis 실행 파일을 찾는다

차례로 확인해 **처음 존재하는 경로**를 `IBIS_EXE` 로 씁니다.

1. `%LOCALAPPDATA%\Programs\Ibis\Ibis.exe` (설치본의 기본 위치)
2. 사용자가 알려 준 설치 폴더의 `Ibis.exe` (압축을 풀어 쓰는 경우)

PowerShell:

```powershell
$ibis = Join-Path $env:LOCALAPPDATA 'Programs\Ibis\Ibis.exe'; Test-Path $ibis
```

없으면 멈추고 사용자에게 Ibis 설치 위치를 묻습니다. Ibis 가 없으면 이 서버는 쓸 수 없습니다
(받는 곳: https://github.com/dodaseo/ibis-releases/releases/latest).

## 2. 서버가 뜨는지 확인한다

```powershell
cmd /c "echo {""jsonrpc"":""2.0"",""id"":1,""method"":""tools/list""} | ""$ibis"" --mcp"
```

PowerShell 의 `'…' | & $ibis --mcp` 꼴은 쓰지 않습니다(창 전용 실행 파일이라 출력이 이어지지 않습니다). bash 에서는
`echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | "$IBIS_EXE" --mcp` 로 됩니다.

`"tools"` 가 든 JSON 한 줄이 나오면 됩니다. 아무것도 나오지 않고 **Ibis 창이 열리면** 이 기능이 없는 오래된 판입니다 —
사용자에게 Ibis 를 업데이트해 달라고 하고 멈춥니다(도움말 › 업데이트 확인). 명령이 끝나지 않으면 기다리지 말고 중단합니다.

## 3. 지금 쓰는 에이전트에 등록한다

자신이 어떤 에이전트인지에 맞는 것 **하나만** 실행합니다. 경로에 공백이 있으니 따옴표를 유지합니다.

| 에이전트 | 명령 |
|---|---|
| Claude Code | `claude mcp add --scope user ibis -- "<IBIS_EXE>" --mcp` |
| Codex | `codex mcp add ibis -- "<IBIS_EXE>" --mcp` |
| Antigravity | `agy mcp add ibis "<IBIS_EXE>" --mcp` |
| 설정 파일을 쓰는 에이전트 | `mcpServers` 에 `"ibis": {"command": "<IBIS_EXE>", "args": ["--mcp"]}` 를 더한다(JSON 에서는 `\` 를 `\` 로) |

이미 `ibis` 가 등록돼 있으면 지우고 다시 등록합니다(경로가 바뀌었을 수 있습니다).

## 4. 사용자에게 Ibis 의 스위치를 켜 달라고 한다

연결은 사용자가 직접 켭니다. **에이전트가 대신 켜지 않습니다** — 서재의 서지가 에이전트 쪽으로 전달되기 시작하는 지점이라
사용자의 결정이어야 합니다. 이렇게 안내합니다.

> Ibis 를 켜고 **설정 › AI › AI 에이전트 연결**을 켜 주세요.

켜졌는지는 이 파일이 있는지로 압니다: `%LOCALAPPDATA%\Ibis\agent-endpoint.json`
(환경변수·설정 파일을 고쳐 대신 켜지 말 것.)

## 5. 확인한다

에이전트를 다시 시작(또는 MCP 다시 연결)한 뒤 `ibis_status` 를 부릅니다. `"ok": true` 와 서재의 문헌 수가 오면 끝입니다.
`"Ibis 에 연결할 수 없습니다"` 가 오면 Ibis 가 꺼져 있거나 4번을 하지 않은 것입니다.

## 쓰는 요령

- 검색은 `ibis_sources` 를 먼저 읽고, 짧은 검색어로 여러 번 합니다.
- 서지를 지어내지 않습니다. 검색 결과에 없는 문헌은 DOI 로만 담습니다.
- PDF 는 받지 않습니다. 모은 컬렉션과 PDF 없는 문헌 수를 알려 주면 사용자가 Ibis 에서 받습니다.
