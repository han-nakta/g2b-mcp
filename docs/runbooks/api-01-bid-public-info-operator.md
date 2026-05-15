# API-01 `bid_public_info` Operator Runbook — MCP Ver.1.0 정리

작성일: 2026-05-15
상태: MCP/온톨로지 evidence 재현용 operator layer 정리

## 1. 목적

API-01 `bid_public_info`는 입찰공고 생명주기의 출발점이며, MCP relationship evidence graph에서 다음 관계의 핵심 seed/source 역할을 한다.

- `BidNotice -> SuccessfulBid`
- `BidNotice -> ContractProcess`
- `PriorSpecification -> BidNotice`
- 향후 public contract bridge key 조사

이 문서는 API-01의 historical count probe와 representative backfill operator를 Ver.1.0 공개 전 정리 기준으로 고정한다. 목표는 full backfill 자체가 아니라, MCP/온톨로지 edge evidence를 재현 가능한 방식으로 설명하는 것이다.

## 2. Operator scripts

```text
skills/g2b-openapi/scripts/probe_bid_public_info_backfill_counts.py
skills/g2b-openapi/scripts/backfill_bid_public_info_core.py
```

### 2.1 Count probe

`probe_bid_public_info_backfill_counts.py`는 API-01의 25개 operation을 월별 window로 나누어 `totalCount`를 조사한다.

기본 정책:

- 2021-05-10 ~ 2026-05-10 5년 범위.
- 월별 window.
- `numOfRows=1`로 count 중심 probe.
- operation endpoint는 각각 별도 호출한다. 모든 operation을 한 호출로 반환하는 aggregate endpoint는 없다.
- raw rows는 저장하지 않는다.
- tracked artifact는 count-only summary다.

출력:

```text
skills/g2b-openapi/references/bid_public_info_backfill_count_probe_2026-05-10.json
skills/g2b-openapi/references/bid_public_info_backfill_count_probe_2026-05-10.md
```

ignored state:

```text
skills/g2b-openapi/cache/backfill_probe/bid_public_info_backfill_count_probe_state.json
```

대표 명령:

```bash
cd /Users/han.nakta/eva
python3 skills/g2b-openapi/scripts/probe_bid_public_info_backfill_counts.py \
  --max-calls 900 \
  --sleep 0.05 \
  --timeout 25
```

### 2.2 Core notice backfill

`backfill_bid_public_info_core.py`는 API-01의 대표 notice-layer operation을 count probe 결과에서 읽어 newest-first 또는 oldest-first로 수집한다.

대표 operation:

```text
getBidPblancListInfoServc
getBidPblancListInfoCnstwk
getBidPblancListInfoThng
getBidPblancListInfoFrgcpt
getBidPblancListInfoEtc
```

기본 정책:

- `page_size=100`을 기본값으로 한다. API-01에서 `numOfRows=1000`은 일부 operation에서 10으로 fallback된 이력이 있다.
- 초반 ontology evidence 확보에는 `--round-robin --per-operation-cap`을 사용해 특정 고용량 operation 하나가 quota를 독점하지 않게 한다.
- raw rows는 gitignored cache에만 저장한다.
- tracked reference에는 counts/status/error summary만 저장한다.
- tracked reference에는 full URL, API key, per-page cache path를 저장하지 않는다.
- 오류율 guard를 두어 네트워크/endpoint 문제 시 장기 실행을 멈춘다.

대표 명령:

```bash
cd /Users/han.nakta/eva
python3 skills/g2b-openapi/scripts/backfill_bid_public_info_core.py \
  --max-calls 1000 \
  --round-robin \
  --per-operation-cap 250 \
  --sleep 0.05 \
  --timeout 25
```

출력:

```text
skills/g2b-openapi/references/bid_public_info_core_backfill_run_latest.json
skills/g2b-openapi/references/bid_public_info_core_backfill_run_latest.md
```

ignored raw/state:

```text
skills/g2b-openapi/cache/backfill_bid_public_info_core/raw/
skills/g2b-openapi/cache/backfill_bid_public_info_core/state.json
skills/g2b-openapi/cache/backfill_bid_public_info_core/runs/
```

## 3. Privacy/security boundary

Tracked artifact에 허용:

- service slug
- operation name
- month/window
- `total_count`, `row_count`, `num_of_rows`
- `result_code`, redacted/short `result_msg`
- error kind/count
- cumulative page/call/row counts
- high-level cache policy: `cache_written: true`, `gitignored cache/`

Tracked artifact에 금지:

- API key value
- auth parameter assignment가 포함된 URL/query string (`ServiceKey`/`serviceKey` parameter value 포함 형태)
- full live request URL
- raw response row
- 담당자명, 전화번호, 이메일, 주소, 사업자등록번호 등 PII 가능 field value
- per-page raw cache file path 목록

2026-05-15 정리에서 두 operator script는 result message의 auth parameter 문자열을 redaction하고, tracked run summary가 raw cache 위치를 policy 수준으로만 설명하도록 조정했다.

## 4. MCP와의 관계

이 operator layer는 Ver.1.0 MCP의 직접 사용자-facing tool이 아니다. 역할은 다음과 같다.

1. API-01 count/backfill evidence를 재현하는 local operator.
2. `relationship_evidence_graph.json`에 들어가는 API-01 source evidence의 provenance.
3. unresolved edge resolver가 API-01 추가 evidence를 요청할 때 사용하는 bounded collection path.

MCP Ver.1.0에서는 raw row backfill 실행을 기본 tool로 열지 않는다. MCP는 privacy-safe summary, edge evidence, unresolved edge recommendation을 노출하고, live/backfill 실행은 local operator workflow로 유지한다.

## 5. 운영 판단

현재 phase에서는 API-01을 더 full-backfill하지 않는다. 이미 API-01~17 대표 evidence phase는 종료되었고, 추가 수집은 다음 조건에서만 수행한다.

- MCP unresolved edge가 API-01의 추가 field/value evidence를 요구한다.
- public contract lifecycle bridge key 조사에 API-01 notice fields가 추가로 필요하다.
- 기존 raw cache의 timeout/parse/error page를 특정 edge 검증 때문에 재시도해야 한다.

그 외에는 MCP Ver.1.0 publication package와 tool contract 안정화를 우선한다.
