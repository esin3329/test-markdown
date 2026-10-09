# Link Doctor

[English](README.md) | [한국어](README.ko.md)

Link Doctor는 Markdown 문서를 재귀적으로 탐색하여 로컬 파일과 이미지 링크를 검사하는 CLI입니다. 입력 파일을 수정하거나 네트워크 요청을 보내지 않습니다.

## 실행 환경

- Node.js 24.x
- npm

의존성을 설치하고 테스트를 실행합니다.

```sh
npm install
npm test
```

## 사용법

```sh
node src/cli.js ./docs
node src/cli.js ./docs --format json
node src/cli.js ./docs --format html --output ./outputs/report.html
```

출력 형식은 `text`(기본값), `json`, `html`입니다. HTML 보고서는 단일 정적 파일이며, `--output`은 HTML 형식에서만 지원합니다. 출력 파일의 상위 폴더는 미리 만들어 두어야 합니다. 입력 문서를 보호하기 위해 검사 루트 안의 Markdown 파일을 덮어쓰는 출력 경로는 거부합니다.

검사기는 `.md` 파일을 재귀적으로 탐색하며 `.git`, `node_modules`, 심볼릭 링크 항목은 제외합니다. 상대 경로는 각 Markdown 파일을 기준으로, `/`로 시작하는 경로는 검사 루트를 기준으로 해석합니다. URL 인코딩된 파일명도 디코딩합니다. 로컬 링크, 이미지, 참조형 링크를 검사하며 코드 블록과 인라인 코드 안의 링크는 무시합니다. 링크 대상은 실제 파일이어야 합니다. 외부 URL, 앵커만 있는 링크, 검사 루트 밖의 경로, 검사 루트 밖으로 연결되는 심볼릭 링크는 건너뜁니다. 파일 링크의 앵커는 검증하지 않으며, 해당 파일이 존재하면 판정 이유에 `anchor not verified`를 표시합니다. 각 검사 결과에는 `source`, `line`, `target`, `kind`, `status`(`ok`, `missing`, `skipped`), `reason`이 포함됩니다.

종료 코드는 누락된 대상이 없으면 `0`, 대상이 하나 이상 없거나 파일이 아니면 `1`, 인자·입력·읽기·출력 오류가 발생하면 `2`입니다.

## 보고서

- 텍스트: 터미널에서 읽을 수 있는 줄 단위 요약이며, 출력 순서가 일정합니다.
- JSON: 검사한 파일 수인 `filesScanned`, 상태별 개수인 `counts`, 정렬된 검사 결과인 `results`를 포함합니다.
- HTML: 보고서 내용을 이스케이프한 단일 정적 문서이며, 실행 가능한 스크립트를 포함하지 않습니다.

[`docs/`](docs/index.md)의 예제 문서는 CLI의 기본 동작 확인에 사용합니다. 테스트용 파일은 [`test/fixtures/scan/`](test/fixtures/scan/index.md)에 있습니다.
