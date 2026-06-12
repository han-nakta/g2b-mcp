import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from g2b_mcp import server


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


class LiveMcpToolTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "G2B_ARTIFACT_DIR": str(ROOT / "artifacts"),
            "G2B_ENABLE_LIVE_FETCH": "",
            "G2B_SERVICE_KEY": "",
            "G2B_BID_PUBLIC_INFO_API_KEY": "",
        }
        self.env_patcher = patch.dict(os.environ, self.env, clear=False)
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_check_api_key_default_disabled_and_unconfigured_without_exposure(self):
        result = server.g2b_check_api_key()
        self.assertFalse(result["configured"])
        self.assertFalse(result["live_fetch_enabled"])
        self.assertFalse(result["key_exposed"])
        self.assertNotIn("key", result)

    def test_call_operation_disabled_live_returns_structured_error_without_network(self):
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        with patch("urllib.request.urlopen") as urlopen:
            result = server.g2b_call_operation_summary(
                "bid_public_info",
                "getBidPblancListInfoThng",
                {"inqryDiv": "1", "inqryBgnDt": "202406010000", "inqryEndDt": "202406012359"},
            )
        self.assertEqual(result["error"]["code"], "LIVE_FETCH_DISABLED")
        self.assertFalse(result["privacy"]["live_fetch_enabled"])
        self.assertNotIn("TOPSECRET", repr(result))
        urlopen.assert_not_called()

    def test_call_operation_enabled_but_missing_key_returns_structured_error(self):
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        with patch("urllib.request.urlopen") as urlopen:
            result = server.g2b_call_operation_summary(
                "bid_public_info",
                "getBidPblancListInfoThng",
                {"inqryDiv": "1", "inqryBgnDt": "202406010000", "inqryEndDt": "202406012359"},
            )
        self.assertEqual(result["error"]["code"], "API_KEY_NOT_CONFIGURED")
        self.assertFalse(result["privacy"]["key_exposed"])
        urlopen.assert_not_called()

    def test_validate_operation_params_reports_missing_unknown_auth_and_caps(self):
        result = server.g2b_validate_operation_params(
            "bid_public_info",
            "getBidPblancListInfoThng",
            {"ServiceKey": "SECRET", "bogus": "x", "numOfRows": 500},
        )
        self.assertFalse(result["valid"])
        self.assertIn("inqryDiv", result["missing_required_non_auth_params"])
        self.assertIn("bogus", result["unknown_params"])
        self.assertEqual(result["auth_param_policy"]["ServiceKey"], "ignored_from_params_use_env")
        self.assertEqual(result["hints"]["numOfRows_max_for_live_summary"], 10)
        self.assertNotIn("SECRET", repr(result))

    def test_safe_request_preview_redacts_env_key_and_never_full_authenticated_url(self):
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        result = server.g2b_build_safe_request_preview(
            "bid_public_info",
            "getBidPblancListInfoThng",
            {"ServiceKey": "SHOULD_NOT_APPEAR", "inqryDiv": "1", "numOfRows": 100},
        )
        self.assertTrue(result["credential_configured"])
        self.assertEqual(result["sanitized_params"]["ServiceKey"], "[REDACTED_FROM_ENV]")
        self.assertNotIn("TOPSECRET", repr(result))
        self.assertNotIn("SHOULD_NOT_APPEAR", repr(result))
        self.assertNotIn("url", result)

    def test_mocked_urllib_response_is_summarized_and_sanitized(self):
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "OK"},
                "body": {
                    "totalCount": 1,
                    "items": [
                        {
                            "bidNtceNm": "Laptop purchase",
                            "dminsttNm": "Seoul Office",
                            "ntceInsttOfclNm": "Private Officer",
                            "ntceInsttOfclTelNo": "redacted phone fixture",
                            "ntceInsttOfclEmailAdrs": "redacted email fixture",
                            "opengDt": "202406011200",
                            "bidClseDt": "202406051200",
                            "presmptPrce": "12345678",
                        }
                    ],
                },
            }
        }
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)) as urlopen:
            result = server.g2b_call_operation_summary(
                "bid_public_info",
                "getBidPblancListInfoThng",
                {"inqryDiv": "1", "inqryBgnDt": "202406010000", "inqryEndDt": "202406012359"},
                num_rows=50,
            )
        self.assertEqual(result["result_code"], "00")
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["item_count"], 1)
        self.assertIn("bidNtceNm", result["field_names"])
        serialized = repr(result)
        self.assertNotIn("TOPSECRET", serialized)
        self.assertNotIn("redacted phone fixture", serialized)
        self.assertNotIn("redacted email fixture", serialized)
        self.assertNotIn("Private Officer", serialized)
        self.assertLessEqual(result["request"]["sanitized_params"]["numOfRows"], 10)
        urlopen.assert_called_once()

    def test_successful_response_values_are_redacted_before_output(self):
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        email_fixture = "buyer" + "@" + "example.test"
        phone_fixture = "010" + "-1234-" + "5678"
        payload = {
            "response": {
                "header": {
                    "resultCode": "00",
                    "resultMsg": f"OK https://example.test?ServiceKey=TOPSECRET contact {phone_fixture}",
                },
                "body": {
                    "totalCount": 1,
                    "items": [
                        {
                            "bidNtceNm": f"Laptop purchase contact {phone_fixture} email {email_fixture}",
                            "dminsttNm": "Seoul Office",
                            "bidwinnrAdrs": "Private Address",
                            "fnlSucsfCorpBizrno": "123-45-67890",
                            "opengDt": "202406011200",
                        }
                    ],
                },
            }
        }
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = server.g2b_call_operation_summary(
                "bid_public_info",
                "getBidPblancListInfoThng",
                {"inqryDiv": "1", "inqryBgnDt": "202406010000", "inqryEndDt": "202406012359"},
            )
        serialized = repr(result)
        self.assertNotIn("TOPSECRET", serialized)
        self.assertNotIn("ServiceKey=", serialized)
        self.assertNotIn(phone_fixture, serialized)
        self.assertNotIn(email_fixture, serialized)
        self.assertNotIn("Private Address", serialized)
        self.assertNotIn("123-45-67890", serialized)

    def test_live_network_exception_does_not_expose_key_or_authenticated_url(self):
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        with patch("urllib.request.urlopen", side_effect=RuntimeError("boom https://example.test?ServiceKey=TOPSECRET")):
            result = server.g2b_call_operation_summary(
                "bid_public_info",
                "getBidPblancListInfoThng",
                {"inqryDiv": "1", "inqryBgnDt": "202406010000", "inqryEndDt": "202406012359"},
            )
        self.assertEqual(result["error"]["code"], "LIVE_FETCH_FAILED")
        serialized = repr(result)
        self.assertNotIn("TOPSECRET", serialized)
        self.assertNotIn("ServiceKey=", serialized)
        self.assertNotIn("https://example.test", serialized)

    def test_search_bid_notices_category_mapping_uses_goods_operation(self):
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        payload = {"response": {"header": {"resultCode": "00", "resultMsg": "OK"}, "body": {"totalCount": 0, "items": []}}}
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = server.g2b_search_bid_notices("laptop", "20240601", "20240602", category="goods", limit=25)
        self.assertEqual(result["service"], "bid_public_info")
        self.assertEqual(result["operation"], "getBidPblancListInfoThng")
        self.assertEqual(result["category"], "goods")
        self.assertLessEqual(result["request"]["sanitized_params"]["numOfRows"], 10)
        self.assertNotIn("TOPSECRET", repr(result))

    def test_search_successful_bids_and_contracts_are_specialized_safe_tools(self):
        os.environ["G2B_ENABLE_LIVE_FETCH"] = "1"
        os.environ["G2B_SERVICE_KEY"] = "TOPSECRET"
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "OK"},
                "body": {
                    "totalCount": 1,
                    "items": [{"bidNtceNm": "Laptop", "dminsttNm": "Seoul Office", "fnlSucsfCorpBizrno": "123-45-67890"}],
                },
            }
        }
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)) as urlopen:
            bids = server.g2b_search_successful_bids("laptop", "20240601", "20240602", category="goods", limit=25)
            contracts = server.g2b_search_contracts("laptop", "20240601", "20240602", category="goods", limit=25)
        self.assertEqual(bids["service"], "scsbid_info")
        self.assertEqual(bids["operation"], "getScsbidListSttusThngPPSSrch")
        self.assertEqual(contracts["service"], "cntrct_info")
        self.assertEqual(contracts["operation"], "getCntrctInfoListThngPPSSrch")
        for result in (bids, contracts):
            self.assertEqual(result["category"], "goods")
            self.assertLessEqual(result["request"]["sanitized_params"]["numOfRows"], 10)
            serialized = repr(result)
            self.assertNotIn("TOPSECRET", serialized)
            self.assertNotIn("123-45-67890", serialized)
        self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
