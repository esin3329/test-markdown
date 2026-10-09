# Link Doctor

[English](README.md) | [한국어](README.ko.md)

Link Doctor는 Markdown 문서를 재귀적으로 탐색하여 로컬 파일과 이미지 링크를 검사하는 CLI입니다. Node.js 기반의 독립형 검사기와, AGY 문서 환경을 위해 Python으로 확장된 위키 컴파일 및 문서 변환, 시맨틱 검색 기능을 제공합니다.

## Node.js CLI (기본 검사기)

입력 파일을 수정하거나 네트워크 요청을 보내지 않고 링크 유효성만 검사합니다.

### 실행 환경
- Node.js 24.x
- npm

의존성을 설치하고 테스트를 실행합니다.
```sh
npm install
npm test
```

### 사용법
```sh
node src/cli.js ./docs
node src/cli.js ./docs --format json
node src/cli.js ./docs --format html --output ./outputs/report.html
```
출력 형식은 `text`(기본값), `json`, `html`입니다. 검사기는 대상 파일의 존재 여부만 판별하며, 상세한 링크 상태를 반환합니다. 

## Python CLI (AGY 지원 확장)

Docling을 이용한 오피스 문서(PDF, DOCX) 마크다운 변환, `wiki-compiler`를 통한 `[[wiki links]]` 컴파일, 그리고 `google/embeddinggemma-2` 임베딩 모델을 활용한 시맨틱 검색을 제공합니다.

### 실행 환경
- Python >= 3.12, < 3.14 (호환되는 Python 전용 가상환경 권장, 3.12.15에서 검증됨)

### 설치
```sh
pip install -e .
python -m unittest discover -s python_tests -v
```
추가 기능은 필요한 경우에만 설치할 수 있습니다:
- `pip install -e '.[ingest]'`: Docling(2.136.0 검증)을 포함하여 PDF/DOCX 변환 기능 활성화
- `pip install -e '.[search]'`: Sentence Transformers (>= 6.1, 6.1.0 검증), Transformers (>= 5.19, 5.19.0 검증) 및 PyTorch (2.14.1 검증)를 포함하여 검색 기능 활성화
- `pip install -e '.[all]'`: 모든 확장 기능 설치

### 명령어 (`link-doctor-py`)
- **검사 (check)**: 일반 및 위키 링크 유효성 검사
  ```sh
  link-doctor-py check <root> [--format text|json|html] [--output FILE]
  ```
  대상 누락이 없으면(외부 링크 및 검사 루트 밖의 심볼릭 링크는 무시됨) `0`, 누락되거나 모호한 대상이 있으면 `1`, 인자/입출력 실패 시 `2`를 반환합니다. 마크다운 원본을 덮어쓰는 HTML 출력은 거부되어 종료 코드 `2`를 반환합니다.
- **컴파일 (compile)**: 마크다운 및 위키 링크를 컴파일하고 그래프/의존성 분석 결과를 출력
  ```sh
  link-doctor-py compile <root> [--output <dir>] [--format text|json|html]
  ```
- **문서 변환 (ingest)**: 오피스 문서를 마크다운으로 변환
  ```sh
  link-doctor-py ingest <source-dir> --output <dir> [--recursive]
  ```
  *참고*: 기본적으로 텍스트 기반의 네이티브 문서 변환을 지원합니다. 스캔된 이미지의 OCR 변환은 외부 OCR 엔진 설치가 필요하며, 기본 제공 기능으로 검증되거나 보장되지 않습니다.
- **검색 (search)**: 시맨틱 검색 인덱스 생성 및 쿼리
  ```sh
  link-doctor-py search <root> <query> [--top-k N] [--index-dir DIR] [--dimension 256] [--device DEVICE]
  ```

> **참고**: `search` 명령어는 `google/embeddinggemma-2` 모델(리비전 `914f7f89142e33e77833254d9c9b90c3cef7303b`)을 사용하며, 비대칭 검색(Asymmetric)의 경우 `SearchQuery`와 제목으로 포맷팅된 `SearchDocument` 프롬프트를 적용하고, 대칭(Symmetric) 관계 후보 검색 시에는 `SentenceSimilarity` 프롬프트를 사용합니다 (상위 검색 결과 내 코사인 유사도 0.55 이상 한정). 이러한 추천 후보들은 미검증 상태로 남으며 절대 자동으로 링크가 생성되거나 덮어쓰이지 않습니다. 생성된 임베딩은 지정된 차원(예: 256)으로 잘림(Truncation) 처리 및 L2 정규화(L2-normalized)됩니다. `.link-doctor/index` 로컬 캐시 식별자는 원본 내용 해시, 모델 ID 및 리비전, 차원, 태스크 프롬프트 등을 포함합니다. 내용이 변경되면 새로운 항목으로 취급되며, 오래된 생성물은 무시되지만 사용자가 폴더를 삭제할 때까지 보존됩니다. 첫 실행 시 네트워크 연결이 필요할 수 있으며, 오프라인 환경을 위해서는 모델 캐시를 미리 준비해야 합니다.
