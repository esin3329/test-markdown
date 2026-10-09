# Documentation Report

이 문서는 Link Doctor의 Python CLI 및 통합 기능에 대한 문서화 내역을 기록합니다.

## 변경 파일
- `README.md`, `README.ko.md`: Node CLI 정보를 유지하면서 Python 확장(검사, 컴파일, 문서 변환, 검색)에 대한 설치, 실행 환경, 명령어 예시, 검색 캐시 메커니즘, 종료 코드 정책 등을 추가했습니다.
- `THIRD_PARTY_NOTICES.md`: 추가된 Python 종속성과 모델, 그리고 고정 리비전 정보(Docling, wiki-compiler, embeddinggemma-2, sentence-transformers, transformers 등)를 명시하고 출처 URL을 포함했습니다.
- `.handoff/DOCUMENTATION_REPORT.md`: 본 문서.

## 확인한 사실 / 공식 출처
- **Docling**: 오피스 문서 변환 라이브러리로, MIT 라이선스를 따릅니다. [https://github.com/docling-project/docling](https://github.com/docling-project/docling)
- **wiki-compiler**: 위키 컴파일 기능을 위해 공급업체 코드로 사용되었으며(리비전 `b2b2b0ecf5f32d69e1cf6d9254216ab902f3d188` 고정), MIT 라이선스를 따릅니다. [https://github.com/Emmimal/wiki-compiler](https://github.com/Emmimal/wiki-compiler)
- **google/embeddinggemma-2**: 시맨틱 검색을 위한 텍스트 임베딩 모델입니다 (2026-10-06 릴리스, 리비전 `914f7f89142e33e77833254d9c9b90c3cef7303b`). Apache 2.0 라이선스입니다. [https://huggingface.co/google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2)

## 실행 안내 검증 범위 및 실제 구현/증거 일치 여부
`.handoff/EXPANSION_READY.md` 및 증거 파일들을 검토하여 다음 사항이 문서 내용과 정확히 일치함을 확인했습니다.
- **Python 환경**: Python 3.12.15에서 검증되었으며 호환성(`>=3.12,<3.14`)이 정확합니다.
- **패키지 및 의존성 버전**: Docling(2.136.0), Sentence Transformers(6.1.0), Transformers(5.19.0), PyTorch(2.14.1) 등의 버전 명세와 설치 명령어(`.[ingest]`, `.[search]`)가 일치합니다.
- **명령어 동작 및 정책**: `check` 명령어의 종료 코드 정책(외부 링크/루트 밖 심볼릭 링크 건너뜀 시 0 반환, 모호한 대상 1 반환, HTML 덮어쓰기 시 2 반환)이 구현 증거와 문서에 동일하게 반영되었습니다. 또한 `ingest` 시 발생한 OCR 엔진 누락 경고를 확인하여, 네이티브 텍스트 문서는 성공적으로 변환되나 스캔된 이미지의 OCR은 검증되지 않았음을 문서에 명시했습니다. `compile` 명령어 시 코드 블록과 인라인 코드를 렉시컬 매칭에서 제외하는 규칙도 추가로 명시했습니다.
- **검색 및 모델 사양**: `SearchQuery` + `SearchDocument` (비대칭) 프롬프트 및 `SentenceSimilarity` (대칭) 프롬프트 사용(상위 검색 결과 내 코사인 0.55 이상 한정, 자동 링크 생성 안 됨), 차원 256 정규화, 로컬 `.link-doctor/index` 캐시 해시 기반 업데이트 등 모델 사양과 동작 방식이 증거(`embeddinggemma-real-search.json` 등)와 완벽히 부합합니다.

## 남은 문서 사실 확인 항목
- 모든 주요 사양과 정책이 검증되었으며, 추가로 남은 미확인 사항은 없습니다.

## 문서 커밋 정보
문서 파일들은 문서 작업 브랜치에 앞선 커밋들로 모두 저장되었으며, 마지막으로 본 보고서가 커밋되어 문서화 작업이 완료되었습니다.
