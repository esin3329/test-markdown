# AGY 독립 리뷰·검증 보고서 — Link Doctor (최종 재검증)

- 갱신 시각: 2026-10-09 12:19 (KST), 최종 상태 동기화, 기준: 최신 `.handoff/IMPLEMENTATION_READY.md`와 현재 `test/scan.test.js`
- **최종 판정: APPROVED — 잔여 발견사항 없음, 차단 사항 없음. G1 해결됨.**
- Git 저장소 없음 → SHA-256 기록. 이번 동기화에서 수정한 파일은 이 문서뿐.

| 파일 | sha256 (앞 16자) | 직전 리뷰 대비 |
|---|---|---|
| src/scan.js | e37613f8421e6683 | 동일 |
| src/report.js | d3afd56a3bfd664f | 동일 |
| src/cli.js | 79d62cbe532717c7 | 동일 |
| package.json | 7978c66c9ec5ace9 | 동일 |
| test/report-cli.test.js | 970cb41113674880 | 동일 |
| test/scan.test.js | 6b2f69445d52e917 | **변경** (테스트 제목을 "UTF-16 code-unit order"로 변경; 로직 변경 없음) |
| README.md / EXPERIMENTS.md / PLAN.md | 61a2d984… / 8b13c268… / 866bc98a… | 동일 |
| .handoff/IMPLEMENTATION_READY.md | 4306ad41e763e65d | **변경** (최신본) |

이전 리뷰의 `test/scan.test.js` 해시 `63b8d4af89c20861`은 구 제목(`by code point`) 기준이었고, 현재 해시 `6b2f69445d52e917`이 개명된 제목을 반영함. 해시 외에 제목 문자열은 `test/scan.test.js:117`에서 직접 확인함.

## 1. 이번에 실제 실행한 검증 (Node v22.22.1 셸 기준)

| 항목 | 결과 |
|---|---|
| `npm test` | ✔ 12/12 통과, fail 0, cancelled 0, skipped 0 |
| `npm run check` (`node src/cli.js ./docs`) | ✔ 종료 코드 0, 2파일, 링크 1개 (ok 1, missing 0, skipped 0) |
| 셸 PATH의 `node --version` | v22.22.1. `./node_modules/.bin/node --version`은 v24.21.0으로 확인함 |

참고: 위 `npm` 실행이 어느 node 바이너리로 돌았는지는 별도로 기록하지 않았으므로, 이 실행을 Node 24 검증으로 주장하지 않음.

## 2. Node 24 증거 — 캡처 파일 검토 (직접 실행 아님)

**Node 24는 내가 직접 실행하지 않았다.** 구현 측이 캡처한 파일을 읽고 내용만 확인함.
- `.handoff/evidence/tests-node24-final.txt`: 12 tests, pass 12, fail 0, cancelled 0, skipped 0. 목록에 개명된 테스트 `orders paths by UTF-16 code-unit order and same-line links by source occurrence` 통과가 포함됨.
- `.handoff/evidence/docs-check-node24-final.txt`: Files scanned 2, Links 1 (ok 1, missing 0, skipped 0), `OK index.md:3 [link] "guide.md"`.
- 이 파일들의 실제 생성 환경(Node 24.21.0)은 `IMPLEMENTATION_READY.md`의 주장과 파일 내용이 일치하나, 생성 과정 자체는 독립 검증하지 못함.

## 3. G1 검증 — 해결됨

- `test/scan.test.js:117-143` 테스트 `orders paths by UTF-16 code-unit order and same-line links by source occurrence`: 소문자 경로 외에 `B/z.md`, `Z.md`를 생성하고, 기대 순서를 `B/z.md, Z.md, a-b/z.md, a.md(link), a.md(image), a/z.md, b.md`로 단언함. 대문자 경로가 소문자보다 앞서야 통과함. 테스트 본문은 제목을 제외하고 G1 수정분과 동일 로직(요청자 설명과 일치; 이전 검토 당시 본문과의 바이트 단위 비교는 하지 않음).
- 구현 `compareText`(`src/scan.js`)는 `<`/`>` 비교이며 `localeCompare` 사용처 없음(`src/scan.js` 해시 불변).
- 같은 경로 집합에 대해 로케일 정렬은 대문자가 뒤(`a-b/z.md, a.md, a/z.md, b.md, B/z.md, Z.md`), 코드 유닛 정렬은 대문자가 앞(`B/z.md, Z.md, a-b/z.md, a.md, a/z.md, b.md`)이라 테스트가 구별 가능함(이전 라운드 Node v22.22.1 확인).
- **변이 확인**(이전 라운드, Node v22.22.1, 프로젝트 외부 임시 사본): `compareText`를 `localeCompare`로 바꾸면 해당 테스트만 실패. 이번에는 재실행하지 않았고, `src/scan.js` 해시가 동일하므로 결론이 유지됨.
- 같은 테스트가 같은 줄 참조 link/image 순서(F3)도 단언함.

## 4. F1–F4 상태

- F1(파일 fragment 앵커 미검증): `marks existing file fragments unverified and missing targets missing`와 `report-cli.test.js`의 텍스트·JSON·HTML 테스트 — 12/12 전체 실행에서 통과.
- F2(빈/쿼리 전용 링크 이유): `skips URLs, anchors, invalid encodings, traversal, and symlink escapes` 통과.
- F3(같은 줄 소스 순서): 위 정렬 테스트 통과.
- F4(UTF-16 코드 유닛 순서): 테스트 제목과 `IMPLEMENTATION_READY.md` 서술이 "UTF-16 code-unit"으로 정확히 일치함. BMP 밖 문자(이모지 등) 정렬 케이스를 직접 실행해 확인하지는 않았으며, 이는 차단 사항이 아님.
- `src/*.js`, `test/report-cli.test.js` 해시가 직전 리뷰와 동일하므로 제품 동작 프로브 결과에 변경 없음.

## 5. 의도된 fixture 누락 링크 (결함 아님)

`test/fixtures/scan/index.md`의 `assets/missing.md`는 스캐너/CLI 테스트용 **의도된 누락 링크**. fixture 스캔이 종료 코드 1이 되는 유일한 원인이며 제품 결함이 아님. 구현 측 증거(`cli-status.txt`: text=1, json=1, html=1)와도 일치함. 이번에 fixture 스캔을 다시 실행하지는 않았음. 실제 `docs/`에는 누락·skip 링크가 없음(위 `npm run check` 확인).

## 6. 남은 발견사항

없음 (G1 해소). 현재 증거(12/12 로컬 통과, 캡처된 Node 24 12/12 및 docs 클린, 해시 일치)가 APPROVED를 뒷받침함.

## 7. 미실행 / 제약

- **Node 24 직접 실행 없음**: Node 24 결과는 캡처 증거 검토에 한함.
- **Orca 병렬 worktree 실험 미실행**(경로가 folder-kind), **Herdr split/detach/reattach 실험 미실행**(`HERDR_ENV=1` 없음). 통과로 간주하지 않음. `EXPERIMENTS.md`가 미실행으로 기록하며 구현 측 서술과 일치.
- Git 저장소가 없어 커밋 고정 불가(SHA-256로 대체).
