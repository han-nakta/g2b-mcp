# G2B MCP Ver.1.0 Publication Plan

작성일: 2026-05-15
상태: draft / MCP Ver.1.0 공개 전 정리 패키지
소유 위치: `/Users/han.nakta/eva`
관련 구현 루트: `skills/g2b-openapi/`, `skills/g2b-procurement-ontology/`

## 1. 목적

API evidence phase를 종료한 뒤 G2B 작업을 바로 Vercel/Supabase 제품으로 넘기기 전에, MCP Ver.1.0의 공개 경계, tool contract, 검증 기준, 배포용 repository 분리 방향을 고정한다.

현재 판단:

- Vercel은 MCP/data graph가 안정화된 뒤 read-only dashboard와 데모 UI에 사용한다.
- Supabase는 raw row 저장소가 아니라 privacy-safe metadata mirror로만 검토한다.
- 지금의 우선순위는 웹 연동이 아니라 MCP Ver.1.0 contract와 공개/비공개 artifact 경계 정리다.

## 2. 현재 기준 상태

- API evidence phase: 종료.
- API-01~17: representative sample/count/evidence 확보.
- API-18 `pub_prcrmnt_stat_info`: public OpenAPI row 미검증으로 unresolved 유지.
- 관계 감사: value-supported/probable edge와 unresolved edge가 분리됨.
- API-01 operator layer: `probe_bid_public_info_backfill_counts.py`와 `backfill_bid_public_info_core.py`를 MCP evidence provenance용 runbook으로 정리함. 상세: `skills/g2b-openapi/references/api-01-bid-public-info-operator-runbook-2026-05-15.md`.
- MCP Ver.1.0 tool contract: `skills/g2b-openapi/references/g2b_mcp_v1_tool_contract_2026-05-15.md`.
- MCP Ver.1.0 대표 질문 세트: `skills/g2b-openapi/references/g2b_mcp_v1_example_queries_2026-05-15.md`.
- MCP readiness: venv Python 기준 `evaluate_g2b_mcp_readiness.py` 100/100, verdict `mcp_ready_after_restart`.
- 시스템 Python 기준 readiness는 `mcp` package 부재로 protocol integration이 실패할 수 있으므로, 운영/검증 명령은 `skills/g2b-openapi/.venv/bin/python`을 사용한다.

검증 명령:

```bash
cd /Users/han.nakta/eva
skills/g2b-openapi/.venv/bin/python skills/g2b-openapi/scripts/evaluate_g2b_mcp_readiness.py
python3 -m py_compile \
  skills/g2b-openapi/scripts/g2b_data_graph.py \
  skills/g2b-openapi/scripts/build_join_map.py \
  skills/g2b-openapi/scripts/mcp_server.py \
  skills/g2b-openapi/scripts/g2b_periodic_collector.py \
  skills/g2b-openapi/scripts/g2b_core_dataset.py
python3 -m unittest \
  tests/test_g2b_openapi_fetcher.py \
  tests/test_g2b_data_graph.py \
  tests/test_g2b_periodic_collector.py
git diff --check
```

## 3. MCP Ver.1.0 공개 tool contract

Ver.1.0은 raw row dump가 아니라 privacy-safe catalog/status/evidence/query contract를 제공한다.

### 3.1 Catalog / API 설명

- `g2b_list_services()`
  - 목적: 18개 G2B service slug와 요약 metadata 조회.
  - 출력: service slug, label, operation count, role summary.
- `g2b_list_operations(service="")`
  - 목적: service별 operation 목록 조회.
  - 입력: optional service slug.
  - 출력: operation name, endpoint metadata, request/response schema summary.
- `g2b_describe_operation(service, operation)`
  - 목적: operation 단위 parameter/schema/quirk 설명.
  - 출력: auth parameter name, date/window quirks, request params, response fields. API key value는 절대 출력하지 않는다.

### 3.2 Dependency-aware collection / dataset status

- `g2b_dependency_aware_collection_plan(service="", write_artifacts=False)`
  - 목적: service별 collection mode, seed key, parent source, unresolved status 조회.
  - 정책: MCP 호출 기본값은 read-only이며 `write_artifacts=False`다.
- `g2b_dataset_status()`
  - 목적: core/periodic dataset readiness와 최근 evidence summary 조회.
  - 출력: counts, status, artifact path, cron readiness summary. raw row는 출력하지 않는다.

### 3.3 Graph / relationship evidence

- `g2b_graph_list_entities()`
  - 목적: procurement entity dictionary 조회.
- `g2b_graph_suggest_mappings(source_service, target_service)`
  - 목적: schema 기반 mapping 후보 조회.
- `g2b_graph_build_join_map(sample_size=50, write_artifacts=False)`
  - 목적: join map 생성/요약. 기본 read-only.
- `g2b_graph_query_join_map(query="")`
  - 목적: join candidate 검색.
- `g2b_graph_list_relationships(status="")`
  - 목적: relationship evidence graph의 edge 목록 조회.
- `g2b_graph_get_edge_evidence(edge_id)`
  - 목적: 특정 edge의 privacy-safe evidence 조회.
- `g2b_graph_list_unresolved_edges()`
  - 목적: unresolved/candidate edge와 다음 조사 이유 조회.
- `g2b_graph_explain_service_role(service)`
  - 목적: API service가 graph에서 맡는 역할 설명.
- `g2b_graph_recommend_next_collection()`
  - 목적: unresolved edge resolver 관점의 다음 collection 후보 추천.

Relationship status vocabulary:

- `verified`: strong live value evidence와 안정적 join key가 있는 관계.
- `probable`: 충분한 value support가 있으나 추가 검증 여지가 있는 관계.
- `candidate`: schema/value 후보이나 승격 전인 관계.
- `lookup_candidate`: master/lookup normalization 후보.
- `unresolved`: public API row, bridge key, seed strategy 등이 아직 해결되지 않은 관계.
- `reconstructed`: 공식 통계 API가 아니라 확보한 17개 API에서 재구성한 통계/관계.

### 3.4 Ontology

- `g2b_ontology_list_nodes()`
- `g2b_ontology_search_nodes(query)`
- `g2b_ontology_get_node_context(node_id)`
- `g2b_ontology_list_edges()`
- `g2b_ontology_query(query)`

정책:

- ontology artifact는 schema/evidence summary 중심이다.
- 담당자명, 전화번호, 이메일, 주소, 사업자등록번호, API key, full auth URL, raw row를 포함하지 않는다.
- API-18 공식 통계는 public row 검증 전까지 `unresolved_period_stat`로 유지한다.

### 3.5 Stabilization

- `g2b_stabilization_list_criteria()`
- `g2b_stabilization_assess_services(use_stored_evidence=True)`

정책:

- live smoke는 opt-in 운영 명령으로만 수행한다.
- MCP client 기본 응답은 stored privacy-safe evidence를 사용한다.

## 4. 공개/비공개 artifact 경계

공개 가능:

- `catalog.json`, `SERVICE_MANUAL.md`, `OPERATIONS.md`에서 비밀값 없는 catalog/schema/operation 설명.
- `entity_dictionary.json`, `graph_schema.json`, `join_map.json`, `relationship_evidence_graph.json`의 privacy-safe summary.
- `g2b_mcp_readiness_report_latest.{json,md}`.
- API별 sample summary/count/evidence markdown/json 중 raw row와 PII를 포함하지 않는 파일.
- ontology pack: `skills/g2b-procurement-ontology/references/ontology_pack.json`.

비공개/local-only:

- `skills/g2b-openapi/.env`.
- `skills/g2b-openapi/cache/**`.
- raw/bronze JSON rows.
- full API key URL 또는 auth parameter value.
- 담당자명/전화번호/이메일/주소 등 PII 가능 필드 값.
- 운영계정 quota 또는 credential 세부값.

## 5. 배포용 repository 분리 방향

현재 Hermes workspace의 `skills/g2b-openapi/`는 구현, 운영 cache, Hermes skill 문서가 한 위치에 있다. 공개/배포용 repository에서는 runtime package와 agent-procedure 문서를 분리한다.

권장 구조:

```text
g2b-procurement-intelligence/
  README.md
  pyproject.toml
  src/
    g2b_openapi/
      catalog.py
      fetcher.py
      normalize.py
    g2b_mcp/
      server.py
      tools.py
    g2b_graph/
      data_graph.py
      ontology.py
      relationship_evidence.py
  artifacts/
    catalog.json
    entity_dictionary.json
    graph_schema.json
    join_map.json
    relationship_evidence_graph.json
    ontology_pack.json
  docs/
    api-catalog.md
    mcp-tool-contract.md
    privacy-boundary.md
    deployment.md
    agent-skills/
  tests/
  .env.example
```

분리 원칙:

- `cache/`와 local state는 repo에 포함하지 않는다.
- Hermes용 SKILL.md는 `docs/agent-skills/` 참고문서로 이동하거나 별도 관리한다.
- public package의 CLI/MCP는 `.env.example`만 제공하고 실제 credential은 사용자 환경에서 주입한다.
- live fetch/backfill은 local operator command로 유지하고, 공개 interface는 catalog/status/evidence 중심으로 제한한다.

## 6. Vercel/Supabase 도입 판단

### 6.1 Vercel

도입 시점: MCP tool contract와 artifact schema가 고정된 뒤.

적합한 용도:

- read-only API catalog explorer.
- ontology/relationship graph viewer.
- edge status/evidence 설명 UI.
- 공모전/시연용 landing page.

부적합한 용도:

- stdio MCP 서버 직접 운영.
- 장시간 collector/backfill.
- raw cache 처리.
- quota-aware batch job.

### 6.2 Supabase

도입 시점: public-safe metadata table 설계가 끝난 뒤.

적합한 테이블:

- `services`
- `operations`
- `mcp_tools`
- `ontology_nodes`
- `ontology_edges`
- `relationship_edges`
- `evidence_summaries`
- `collection_status`

금지:

- raw G2B response row.
- PII 가능 필드 값.
- API key/full auth URL.
- ignored cache contents.

권장 접근:

1. local artifact JSON을 source of truth로 유지한다.
2. Supabase에는 공개 가능한 summary만 mirror한다.
3. Vercel은 Supabase 또는 static JSON artifact를 읽는 read-only UI로 시작한다.
4. live fetch/backfill control은 웹 UI에서 바로 열지 않고 local operator workflow로 유지한다.

## 7. cron/scheduler 상태 점검 항목

PRD에는 다음 daily job이 기록되어 있다.

- Core Dataset Daily Collection: `f5aefaef56d5`, 07:10 KST.
- Periodic17 Daily Window Collection: `205760dd60d2`, 07:20 KST.

2026-05-15 현재 Hermes cron listing에서는 job count가 0으로 확인되었다. 가능한 해석:

- scheduler profile/state가 바뀌었거나 초기화되었다.
- 문서가 과거 운영 상태를 기록하고 있고 현재 scheduler에는 등록되어 있지 않다.
- 다른 Hermes profile 또는 별도 cron/system scheduler에 남아 있을 수 있다.

다음 조치:

1. Hermes profile별 cron state 위치 확인.
2. 필요한 경우 두 daily job을 재등록하되, 먼저 script path와 no-agent 출력 정책을 재검증한다.
3. PRD에는 “문서상 job”과 “현재 scheduler 등록 상태”를 분리해서 기록한다.

## 8. 다음 실행 순서

1. G2B 관련 untracked/tracked 변경사항을 공개 가능 artifact, 운영 local-only artifact, 비-G2B 변경으로 분류한다.
2. readiness/test/secret scan을 venv 기준으로 재실행한다.
3. PRD에서 이 문서, API-01 operator runbook, MCP tool contract, example query set을 Ver.1.0 공개 전 entrypoint로 연결한다.
4. G2B 관련 파일만 별도 commit한다.
5. push는 사용자가 명시적으로 원하거나 G2B checkpoint push 정책에 따라 진행한다.
6. 이후 배포용 repository skeleton 또는 Vercel read-only dashboard prototype을 시작한다.
