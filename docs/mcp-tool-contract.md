# G2B MCP Ver.1.0 Tool Contract

작성일: 2026-05-15
상태: Ver.1.0 local/publication contract baseline

## 1. Contract 원칙

G2B MCP Ver.1.0은 raw row dump 서비스가 아니다. 공개/사용자-facing contract는 다음 정보로 제한한다.

- API catalog/status
- operation schema/parameter 설명
- dependency-aware collection mode
- dataset/readiness/status summary
- relationship evidence graph
- ontology node/edge/query summary
- stabilization/readiness criteria

금지:

- API key value
- full auth URL
- raw G2B response row
- 담당자명/전화번호/이메일/주소/사업자등록번호 등 PII 가능 값
- ignored cache contents
- quota credential details

기본 동작은 read-only다. artifact write, live smoke, live fetch, backfill은 CLI/local operator에서 명시적으로 수행한다.

## 2. Tool groups

## 2.1 Catalog / API 설명

### `g2b_list_services()`

목적: 18개 G2B service slug와 요약 metadata를 반환한다.

입력: 없음.

출력 요건:

- service slug
- 한국어/영문 label 또는 description
- operation count
- service role summary if available

금지: credential, raw URL with auth query.

### `g2b_list_operations(service="")`

목적: 전체 또는 특정 service의 operation 목록을 반환한다.

입력:

- `service`: optional service slug. 빈 값이면 전체 목록 또는 service별 grouped summary.

출력 요건:

- service slug
- operation name
- operation label/description
- endpoint metadata without auth query
- request/response schema summary

### `g2b_describe_operation(service, operation)`

목적: 단일 operation의 호출/스키마/quirk를 설명한다.

입력:

- `service`: service slug
- `operation`: operation name

출력 요건:

- request parameters
- response fields
- response format/type quirk
- auth parameter name only, never value
- known date/window/page-size quirks

## 2.2 Dependency / dataset status

### `g2b_dependency_aware_collection_plan(service="", write_artifacts=False)`

목적: service/operation별 collection mode와 seed dependency를 설명한다.

입력:

- `service`: optional service slug
- `write_artifacts`: default `False`

출력 요건:

- collection mode: `daily_window_parent`, `parent_seed_batch`, `reference_snapshot`, `period_window`, `unresolved_period_stat` 등
- required seed keys
- parent seed source
- verified representative query status
- unresolved reason if applicable

정책: MCP client 호출 기본값은 read-only. artifact write는 operator/local 작업에서만 명시적으로 수행한다.

### `g2b_dataset_status()`

목적: core/periodic dataset의 readiness와 최신 evidence summary를 반환한다.

출력 요건:

- dataset names
- latest collection window/status/counts
- cron readiness summary
- artifact paths or policy-level locations

금지: raw rows, per-page raw cache path 목록.

## 2.3 Data graph / relationship evidence

### `g2b_graph_list_entities()`

목적: procurement entity dictionary를 조회한다.

출력 예: `BidNotice`, `SuccessfulBid`, `Contract`, `DemandOrganization`, `ProcurementCompany`, `Product`, `Region`.

### `g2b_graph_suggest_mappings(source_service, target_service)`

목적: 두 service 간 schema-based mapping 후보를 반환한다.

입력:

- `source_service`
- `target_service`

출력 요건:

- candidate fields
- schema score
- join type
- status: schema-only/candidate/probable/verified 등

### `g2b_graph_build_join_map(sample_size=50, write_artifacts=False)`

목적: join map을 build/summary한다.

정책:

- 기본은 read-only summary.
- `write_artifacts=True`는 local operator 의도일 때만 사용.
- raw rows를 저장하거나 반환하지 않는다.

### `g2b_graph_query_join_map(query="")`

목적: join map 후보 검색.

입력: keyword query.

출력: matching candidates and evidence summaries.

### `g2b_graph_list_relationships(status="")`

목적: relationship evidence graph의 edge 목록을 status별로 조회한다.

입력:

- `status`: optional one of `verified`, `probable`, `candidate`, `lookup_candidate`, `unresolved`, `reconstructed`.

출력 요건:

- edge id
- source/target entity
- source/target service
- join keys
- status
- short evidence summary

### `g2b_graph_get_edge_evidence(edge_id)`

목적: 특정 edge의 privacy-safe evidence를 반환한다.

출력 요건:

- evidence source artifacts
- counts/rates if available
- matched/ambiguous/unmatched summary
- promotion rationale
- limitations

금지: matched raw values or sample rows.

### `g2b_graph_list_unresolved_edges()`

목적: unresolved/candidate edge와 해결에 필요한 후속 작업을 반환한다.

출력 요건:

- unresolved edge id
- blocker reason
- recommended next collection/probe
- expected seed/source service

### `g2b_graph_explain_service_role(service)`

목적: 특정 service가 graph에서 맡는 역할을 설명한다.

예:

- source event stream
- seed-detail child
- reference taxonomy
- lookup/master table
- unresolved official statistics

### `g2b_graph_recommend_next_collection()`

목적: open-ended sampling이 아니라 unresolved edge resolver 관점의 다음 수집 후보를 추천한다.

출력 요건:

- priority
- target edge/question
- collection mode
- bounded command/runbook pointer
- reason

## 2.4 Ontology tools

### `g2b_ontology_list_nodes()`

목적: ontology pack node 목록 조회.

### `g2b_ontology_search_nodes(query)`

목적: node label/alias/search hint 기반 검색.

### `g2b_ontology_get_node_context(node_id)`

목적: 한 node의 neighbors, edges, aliases, source services 조회.

### `g2b_ontology_list_edges()`

목적: ontology edge 목록과 status 조회.

### `g2b_ontology_query(query)`

목적: schema/evidence summary 기반 natural-language style query.

정책:

- ontology artifact는 schema/evidence summary다.
- API-18 official statistics는 public row 검증 전까지 unresolved로 답한다.
- 17개 API 기반 집계는 `reconstructed`로 답한다.

## 2.5 Stabilization tools

### `g2b_stabilization_list_criteria()`

목적: MCP readiness/stabilization gate 목록을 반환한다.

### `g2b_stabilization_assess_services(use_stored_evidence=True)`

목적: stored evidence 기준 service readiness scorecard를 반환한다.

정책:

- 기본은 stored evidence.
- live smoke는 CLI에서 opt-in으로 실행한다.

## 3. Relationship status vocabulary

| status | 의미 | Ver.1.0 응답 정책 |
|---|---|---|
| `verified` | live value evidence와 안정적 join key가 있는 관계 | confidence/rate/count를 요약해 설명 |
| `probable` | 충분한 value support가 있으나 추가 검증 여지가 있음 | probable로 명시하고 limitation 표시 |
| `candidate` | schema/value 후보이나 승격 전 | 후속 검증 필요 |
| `lookup_candidate` | master/reference normalization 후보 | lookup completeness 한계 표시 |
| `unresolved` | bridge key/public row/seed strategy 미해결 | blocker와 next collection 추천 |
| `reconstructed` | 공식 통계 API가 아니라 17개 API 기반 재구성 | official statistic과 명확히 구분 |

## 4. Ver.1.0 acceptance checks

Ver.1.0 공개 전 최소 gate:

1. `evaluate_g2b_mcp_readiness.py` score 100/100 또는 blocking issue 없음.
2. 21/21 MCP tools discovered.
3. plain helper smoke 통과.
4. stdio MCP protocol smoke 통과.
5. semantic assertions 통과.
6. privacy scan 통과: secret/auth/PII pattern 0.
7. `py_compile` 통과.
8. unit tests 통과.
9. `git diff --check` 통과.
10. publication plan/PRD/runbook가 최신 상태.
