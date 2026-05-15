# G2B MCP Ver.1.0 Example Queries

작성일: 2026-05-15
상태: Ver.1.0 tool contract 검증용 대표 질문 세트

## 1. 목적

이 문서는 MCP Ver.1.0 공개 전 tool contract가 실제 사용자 질문을 안정적으로 처리하는지 확인하기 위한 대표 query set이다. 각 질문은 raw row가 아니라 privacy-safe catalog/status/evidence/ontology summary로 답해야 한다.

## 2. Catalog/API 질문

### Q1. 어떤 G2B 서비스들이 등록되어 있어?

권장 tool:

```text
g2b_list_services()
```

기대 답변:

- 18개 service slug와 설명.
- operation count.
- 서비스 역할 요약.

금지:

- API key.
- live auth URL.

### Q2. `bid_public_info`에는 어떤 operation이 있어?

권장 tool:

```text
g2b_list_operations(service="bid_public_info")
```

기대 답변:

- API-01 operation 목록.
- 공사/용역/물품/외자/기타 notice-layer operation 구분.
- change history, PPSSrch, detail 계열이 별도 operation임을 설명.

### Q3. `getBidPblancListInfoCnstwk`는 어떻게 호출해야 해?

권장 tool:

```text
g2b_describe_operation(service="bid_public_info", operation="getBidPblancListInfoCnstwk")
```

기대 답변:

- 필수/선택 parameter.
- date window parameter.
- page size quirk: API-01은 `numOfRows=100`이 안전했던 evidence가 있고, `1000` fallback 이력이 있음.
- auth parameter name only.

## 3. Relationship/evidence 질문

### Q4. 입찰공고와 낙찰정보는 어떤 key로 연결돼?

권장 tool:

```text
g2b_graph_get_edge_evidence(edge_id="BidNotice_to_SuccessfulBid")
```

또는:

```text
g2b_graph_list_relationships(status="probable")
```

기대 답변:

- `bidNtceNo + bidNtceOrd` composite key.
- sampled value evidence의 match rate/count summary.
- 현재 status가 verified/probable인지 명시.
- raw matched values는 표시하지 않음.

### Q5. 민간 입찰과 민간 낙찰도 연결돼?

권장 tool:

```text
g2b_graph_list_relationships(status="probable")
g2b_graph_get_edge_evidence(edge_id="PrivateBidNotice_to_PrivateSuccessfulBid")
```

기대 답변:

- `PrivateBidNotice -> PrivateSuccessfulBid` relationship.
- `bidNtceNo + bidNtceOrd` 후보/근거.
- public lifecycle과 별도 private lifecycle임을 설명.

### Q6. 계약정보는 왜 아직 입찰공고와 직접 verified가 아니야?

권장 tool:

```text
g2b_graph_list_unresolved_edges()
g2b_graph_get_edge_evidence(edge_id="BidNotice_to_Contract")
```

기대 답변:

- sampled contract APIs에서 notice key가 충분히 populated되지 않았다는 blocker.
- 조사 후보: `pub_data_opn_std` contract fields, `untyCntrctNo`, `dcsnCntrctNo`, `cntrctRefNo` 등 bridge key.
- 다음 collection은 full sampling이 아니라 unresolved edge resolver 방식으로 제한.

### Q7. 다음에 데이터를 더 모아야 한다면 어디부터야?

권장 tool:

```text
g2b_graph_recommend_next_collection()
```

기대 답변:

- public/private contract lifecycle bridge key.
- `usr_info` master lookup completeness.
- API-18 official stat mismatch는 public row 검증 전까지 unresolved.
- 각 항목별 bounded next action.

## 4. Ontology 질문

### Q8. `BidNotice` node 주변 context를 보여줘.

권장 tool:

```text
g2b_ontology_search_nodes(query="BidNotice")
g2b_ontology_get_node_context(node_id="BidNotice")
```

기대 답변:

- 관련 aliases.
- source services: `bid_public_info`, `pub_data_opn_std` 등.
- outgoing/incoming edges: `SuccessfulBid`, `DemandOrganization`, `ContractProcess`, `PriorSpecification` 등.
- edge status 구분.

### Q9. 품목분류번호 `prdctClsfcNo`는 어떤 관계에 쓰여?

권장 tool:

```text
g2b_ontology_query(query="prdctClsfcNo product classification relationships")
g2b_graph_list_relationships()
```

기대 답변:

- product classification/service-to-product links.
- `thng_list_info`가 dictionary/reference 성격임을 설명.
- `shopping_mall_prdct_info`, `prdct_mng_info`, `price_info`와의 관계 후보.

## 5. Statistics/API-18 질문

### Q10. 공공조달통계 API는 사용할 수 있어?

권장 tool:

```text
g2b_dependency_aware_collection_plan(service="pub_prcrmnt_stat_info")
g2b_graph_explain_service_role(service="pub_prcrmnt_stat_info")
```

기대 답변:

- status: `unresolved_period_stat`.
- public OpenAPI는 `resultCode=00`이어도 `totalCount=0`이 확인된 상태.
- DataHub/MSTR report layer에는 대응 개념/보고서가 있으나 public OpenAPI row 검증과는 별개.
- official statistic source로 승격하지 않음.

### Q11. 한국남부발전/KOSPO 통계는 만들 수 있어?

권장 tool:

```text
g2b_ontology_query(query="KOSPO demand organization reconstructed procurement statistics")
g2b_graph_list_relationships(status="reconstructed")
```

기대 답변:

- official `PubPrcrmntStatInfoService` 결과와 reconstructed stats를 구분.
- 가능한 경우 17개 API 기반 reconstructed statistics로 접근.
- demand organization code/name normalization은 `usr_info` lookup candidate로 설명.
- DataHub UI evidence는 public OpenAPI 정상성의 증거가 아니라 mismatch evidence로 설명.

## 6. Readiness/운영 질문

### Q12. MCP는 지금 공개 가능한 상태야?

권장 tool/command:

```text
g2b_stabilization_assess_services(use_stored_evidence=True)
skills/g2b-openapi/.venv/bin/python skills/g2b-openapi/scripts/evaluate_g2b_mcp_readiness.py
```

기대 답변:

- latest readiness score.
- 21/21 tools discovered 여부.
- stdio MCP protocol smoke 여부.
- privacy scan 결과.
- fresh Hermes session/gateway restart 필요 여부.

### Q13. Vercel/Supabase를 지금 붙여야 해?

권장 답변:

- 지금은 필수 아님.
- MCP tool contract/artifact schema가 source of truth.
- Vercel은 read-only dashboard/demo UI에 적합.
- Supabase는 public-safe metadata mirror에만 적합.
- raw cache/backfill/live quota control은 local operator로 유지.

## 7. Regression expectations

위 질문 세트는 Ver.1.0 publication package의 smoke checklist로 사용한다.

통과 기준:

- 모든 답변이 raw row 없이 summary/evidence 중심이다.
- status vocabulary가 일관된다.
- API-18은 항상 unresolved/reconstructed distinction을 보존한다.
- unresolved edge 질문은 bounded next action을 제시한다.
- Vercel/Supabase 질문은 local MCP contract 안정화 이후로 defer한다.
