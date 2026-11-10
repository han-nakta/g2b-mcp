# Catalog verification (2026-11-09 / 2026-11-10)

This document records how `artifacts/catalog.json` (18 services, 195 operations) was checked against the
provider's own sources and against live responses, what is still unverified, and how to repeat the checks.
No raw rows, contact values, credentials or authenticated URLs are stored in the repository.

## What was verified

| Check | Source | Coverage |
|---|---|---|
| Endpoint exists | keyless/bogus-key gateway probe (`SERVICE_KEY_IS_NULL` vs `NO_OPENAPI_SERVICE_ERROR`) | 195 / 195 |
| Daily traffic limit | data.go.kr 활용신청 현황 (운영계정) | 195 / 195 (100,000; 1,000,000 for usr_info and pub_data_opn_std) |
| Request parameter names | data.go.kr 활용신청 현황 (`selectParamterList`), compared per operation | 195 / 195 (`request_params_verified`) |
| Response fields | provider OpenAPI reference documents (docx) | 193 operations (`response_fields_status: reference_doc_*`) |
| Live response | one call per operation with `numOfRows=1`, field names compared | 161 / 195 (`live_response_check`) |

Notes:

- The public hub (data.g2b.go.kr) lags behind the live gateway. `BidPublicInfoService02`, `ThngListInfoService02`
  and `UsrInfoService02` carry `02` in the service and operation names; older names are kept in `previous_version`.
- Request parameter *required* flags were not verified: the reference documents mark many conditionally required
  parameters as optional. Only parameter names were matched. In practice some operations need more than the flags say
  (see "Operation notes").
- Response fields were compared against **one sampled item** per operation. A field missing from that one item is not
  treated as wrong, because optional fields can be omitted. 20 operations returned fields that the documents did not list;
  these were added with `source: live_response` (field names only). Where the live name differs from the document only by
  letter case, the entry has `case_variant_of`.
- Fields that exist only in the earlier catalog were kept and marked `in_reference_doc: false` so name-based privacy
  checks do not lose them.

## Operation notes learned from live calls

- `inqryDiv` values need the matching date pair (`inqryBgnDt`/`inqryEndDt`, format `YYYYMMDDHHMM`) even though the pair is
  listed as optional.
- `getSpcifyPrdlstPrcureInfoList` and `getSpcifyPrdlstPrcureTotList` return a required-value error unless a name filter
  (for example `prdctClsfcNoNm`) is supplied together with `inqryPrdctDiv`.
- `getDataSetOpnStdScsbidInfo` rejects an opening-date range of about a week (`07` out-of-range); a one-day window works.
- Detail operations (for example `getPrcrmntReqInfoListThngDetail`) need an identifier taken from the matching list operation.
- The reference document for the order-plan service lists `getOrderPlanSttusAtchFileList`, which is not part of the approved
  service and is not in the catalog.

## Not verified against a live response (34 operations)

Every call below returned result code `00` (normal) with zero rows for all windows and identifiers tried
(last 7/30/360 days, calendar years 2024 and 2025, `inqryDiv` 1-4, identifiers taken from list responses).
Their response fields therefore come from the reference documents only and are marked
`live_response_check.result: not_verified`.

| # | Service | Operation | Name |
|---|---|---|---|
| 1 | `cntrct_procss_intg_open` | `getCntrctProcssIntgOpenFrgcpt` | 계약과정통합공개정보에 대한 외자조회 |
| 2 | `cntrct_procss_intg_open` | `getCntrctProcssIntgOpenServc` | 계약과정통합공개정보에 대한 용역조회 |
| 3 | `cntrct_procss_intg_open` | `getCntrctProcssIntgOpenCnstwk` | 계약과정통합공개정보에 대한 공사조회 |
| 4 | `thng_list_info` | `getPrdctIndvAtrbInfoList02` | 품목개별속성정보 조회 |
| 5 | `scsbid_info` | `getOpengResultListInfoFailing` | 개찰결과 유찰 목록 조회 |
| 6 | `scsbid_info` | `getOpengResultListInfoRebid` | 개찰결과 재입찰 목록 조회 |
| 7 | `cntrct_info` | `getCntrctInfoListThngDltHstry` | 계약현황에 대한 물품삭제이력조회 |
| 8 | `cntrct_info` | `getCntrctInfoListCnstwkChgHstry` | 계약현황에 대한 공사변경이력조회 |
| 9 | `cntrct_info` | `getCntrctInfoListCnstwkDltHstry` | 계약현황에 대한 공사삭제이력조회 |
| 10 | `cntrct_info` | `getCntrctInfoListServcChgHstry` | 계약현황에 대한 용역변경이력조회 |
| 11 | `cntrct_info` | `getCntrctInfoListServcDltHstry` | 계약현황에 대한 용역삭제이력조회 |
| 12 | `cntrct_info` | `getCntrctInfoListFrgcptChgHstry` | 계약현황에 대한 외자변경이력조회 |
| 13 | `cntrct_info` | `getCntrctInfoListFrgcptDltHstry` | 계약현황에 대한 외자삭제이력조회 |
| 14 | `order_plan_sttus` | `getOrderPlanSttusListCnstwkPPSSrch` | 나라장터 검색조건에 의한 발주계획현황에 대한 공사조회 |
| 15 | `order_plan_sttus` | `getOrderPlanSttusListServcPPSSrch` | 나라장터 검색조건에 의한 발주계획현황에 대한 용역조회 |
| 16 | `order_plan_sttus` | `getOrderPlanSttusListFrgcptPPSSrch` | 나라장터 검색조건에 의한 발주계획현황에 대한 외자조회 |
| 17 | `bid_public_info` | `getBidPblancListPPIFnlRfpIssAtchFileInfo02` | 입찰공고목록 정보에 대한 혁신장터 최종제안요청서 교부 첨부파일정보조회 |
| 18 | `prcrmnt_req_info` | `getPrcrmntReqInfoListFrgcptDetail` | 조달요청에 대한 외자세부조회 |
| 19 | `pub_prcrmnt_stat_info` | `getTotlPubPrcrmntSttus` | 전체 공공조달 현황 |
| 20 | `pub_prcrmnt_stat_info` | `getInsttDivAccotPrcrmntSttus` | 기관구분별 조달 현황 |
| 21 | `pub_prcrmnt_stat_info` | `getEntrprsDivAccotPrcrmntSttus` | 기업구분별 조달 현황 |
| 22 | `pub_prcrmnt_stat_info` | `getCntrctMthdAccotSttus` | 계약방법별 현황 |
| 23 | `pub_prcrmnt_stat_info` | `getRgnLmtSttus` | 지역제한 현황 |
| 24 | `pub_prcrmnt_stat_info` | `getRgnDutyCmmnCntrctSttus` | 지역의무공동계약 현황 |
| 25 | `pub_prcrmnt_stat_info` | `getPrcrmntObjectBsnsObjAccotSttus` | 조달목적물(업무대상)별 현황 |
| 26 | `pub_prcrmnt_stat_info` | `getDminsttAccotEntrprsDivAccotArslt` | 수요기관별 기업구분별 실적 |
| 27 | `pub_prcrmnt_stat_info` | `getDminsttAccotCntrctMthdAccotArslt` | 수요기관별 계약방법별 실적 |
| 28 | `pub_prcrmnt_stat_info` | `getDminsttAccotBsnsObjAccotArslt` | 수요기관별 업무대상별 실적 |
| 29 | `pub_prcrmnt_stat_info` | `getDminsttAccotSystmTyAccotArslt` | 수요기관별 시스템유형별 실적 |
| 30 | `pub_prcrmnt_stat_info` | `getPrcrmntEntrprsAccotCntrctMthdAccotArslt` | 조달기업별 계약방법별 실적 |
| 31 | `pub_prcrmnt_stat_info` | `getPrcrmntEntrprsAccotBsnsObjAccotArslt` | 조달기업별 업무대상별 실적 |
| 32 | `pub_prcrmnt_stat_info` | `getPrdctIdntNoServcAccotArslt` | 품목 및 서비스별 실적 |
| 33 | `prvt_bid_ntce` | `getPrvtBidPblancListInfoEtc` | 민간입찰공고정보에 대한 기타조회 |
| 34 | `prvt_bid_ntce` | `getPrvtBidPblancListInfoEtcPPSSrch` | 나라장터 검색조건에 의한 민간입찰공고정보에 대한 기타조회 |

Open items (owner: repository maintainer):

1. Domain review of the zero-row operations: decide whether they are genuinely empty, need rare conditions, or need
   inputs this check could not supply.
2. Ask the data.go.kr developer inquiry board whether the public-procurement statistics service
   (`PubPrcrmntStatInfoService`, 14 operations above) is serving data. Year-only requests work only for
   `getTotlPubPrcrmntSttus`; the others require `srchBssYmBgn`/`srchBssYmEnd` and return zero rows for every period tried.

## How to repeat the check

```bash
# key stays in a local 0600 file; never paste it into chat or commit it
mkdir -p ~/.config/g2b-mcp && printf 'G2B_SERVICE_KEY=\n' > ~/.config/g2b-mcp/.env && chmod 600 ~/.config/g2b-mcp/.env
# edit the file to add the key, then:
python scripts/g2b_catalog_live_check.py out.json                 # all operations, one item each
WINDOW_DAYS=300 python scripts/g2b_catalog_live_check.py out.json getCntrctInfoListThngDltHstry
```

The script prints only a status count; `out.json` holds status, result code and response field names, never values.
Keep `out.json` outside the repository unless it has been reviewed. Rotate the key at data.go.kr after a verification run.

## Public references consulted

Other public projects register these operation names but none reports that the zero-row operations return data:
`solid-hwan/nara-data-collector` (docs/coverage.md lists 144 registered operations, 4 verified live),
`Electerior/g2bmaster-backend`, `ChangooLee/mcp-kr-g2b`, `alphago2580/naramarketmcp`, `Hbin77/margin-radar`.
The official data.go.kr page for the statistics service (dataset 15129412) does not mention empty results.
