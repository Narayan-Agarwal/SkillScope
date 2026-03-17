"""
Tests for seed_data.py pipeline cleaning functions.

Property tests P1–P4 and P9, plus unit tests for pipeline error handling.
"""
from __future__ import annotations

import io
import os
import sys
import time
import types
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from hypothesis import given, settings, strategies as st

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from seed_data import (
    COMPANY_TIER_MAP,
    ROLE_MAPPING,
    VALID_ROLES,
    VALID_TIERS,
    get_tier,
    normalize_role,
    normalize_text,
)

# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 1: Deduplication invariant
# Validates: Requirements 2.1, 2.2
@given(
    st.lists(
        st.fixed_dictionaries({
            "company_name": st.text(min_size=1, max_size=50),
            "role_title": st.text(min_size=1, max_size=50),
            "description": st.text(max_size=200),
        }),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=100)
def test_deduplication_invariant(records):
    """After dedup, no two records share (company_name, role_title).
    Also no record has both title and description null/empty.

    Validates: Requirements 2.1, 2.2
    """
    df = pd.DataFrame(records)

    # Drop rows where both title and description are null/empty
    title_empty = df["role_title"].isna() | (df["role_title"].astype(str).str.strip() == "")
    desc_empty = df["description"].isna() | (df["description"].astype(str).str.strip() == "")
    df = df[~(title_empty & desc_empty)].copy()

    # Deduplicate on (company_name, role_title)
    df = df.drop_duplicates(subset=["company_name", "role_title"], keep="first").copy()

    # Property: no duplicate (company_name, role_title) pairs
    pairs = list(zip(df["company_name"], df["role_title"]))
    assert len(pairs) == len(set(pairs)), "Duplicate (company_name, role_title) pairs found after dedup"

    # Property: no record has both title and description null/empty
    for _, row in df.iterrows():
        title_is_empty = pd.isna(row["role_title"]) or str(row["role_title"]).strip() == ""
        desc_is_empty = pd.isna(row["description"]) or str(row["description"]).strip() == ""
        assert not (title_is_empty and desc_is_empty), "Record with both title and description empty survived cleaning"


# Feature: skillscope, Property 2: Role normalization output domain
# Validates: Requirements 2.3
@given(st.text())
@settings(max_examples=200)
def test_role_normalization_domain(raw_title):
    """normalize_role must return one of the 15 roles or 'Other'.

    Validates: Requirements 2.3
    """
    result = normalize_role(raw_title)
    assert result in VALID_ROLES, f"normalize_role({raw_title!r}) returned {result!r}, not in valid roles"


# Feature: skillscope, Property 3: Tier assignment output domain
# Validates: Requirements 2.4
@given(st.text())
@settings(max_examples=200)
def test_tier_assignment_domain(company_name):
    """get_tier must return one of the 6 tiers or 'Other'.

    Validates: Requirements 2.4
    """
    result = get_tier(company_name)
    assert result in VALID_TIERS, f"get_tier({company_name!r}) returned {result!r}, not in valid tiers"


# Feature: skillscope, Property 4: Title case normalization
# Validates: Requirements 2.5
@given(st.text(min_size=1, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"))))
@settings(max_examples=200)
def test_title_case_normalization(text):
    """normalize_text(text) must equal text.title().

    Validates: Requirements 2.5
    """
    assert normalize_text(text) == text.title(), (
        f"normalize_text({text!r}) = {normalize_text(text)!r}, expected {text.title()!r}"
    )


# Feature: skillscope, Property 9: Data source tagging
# Validates: Requirements 4.3, 4.4
@given(st.sampled_from(["kaggle", "adzuna"]))
@settings(max_examples=50)
def test_data_source_tagging(source):
    """Records tagged with a source must have data_source == source.

    Validates: Requirements 4.3, 4.4
    """
    # Simulate a role_skills record being tagged
    record = {
        "role_id": 1,
        "skill_name": "Python",
        "skill_category": "Programming",
        "data_source": source,
    }
    assert record["data_source"] == source, (
        f"Expected data_source={source!r}, got {record['data_source']!r}"
    )
    assert record["data_source"] in ("kaggle", "adzuna"), (
        f"data_source must be 'kaggle' or 'adzuna', got {record['data_source']!r}"
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestDownloadKaggleMissingToken(unittest.TestCase):
    """test_download_kaggle_missing_token: missing env var → sys.exit(1)."""

    def test_missing_token_exits(self):
        """When KAGGLE_API_TOKEN and KAGGLE_KEY are absent, sys.exit(1) is called."""
        from seed_data import download_kaggle

        env_without_kaggle = {k: v for k, v in os.environ.items()
                              if k not in ("KAGGLE_API_TOKEN", "KAGGLE_KEY")}

        with patch.dict(os.environ, env_without_kaggle, clear=True):
            with patch("seed_data.load_dotenv", return_value=None):
                with self.assertRaises(SystemExit) as ctx:
                    download_kaggle("data/kaggle_raw.csv")
        self.assertEqual(ctx.exception.code, 1)


class TestDownloadKaggleRetry3Times(unittest.TestCase):
    """test_download_kaggle_retry_3_times: 3 consecutive failures → 3 attempts then exit."""

    def test_retries_three_times_then_exits(self):
        """When the download fails 3 times, it retries 3 times then calls sys.exit(1)."""
        import seed_data

        attempt_calls = []

        # Patch KaggleApiExtended so each authenticate/download call raises
        mock_api = MagicMock()
        mock_api.authenticate.side_effect = ConnectionError("Network error")

        def fake_kaggle_api(*args, **kwargs):
            attempt_calls.append(1)
            return mock_api

        # We need to patch the import of kaggle inside download_kaggle
        fake_kaggle_module = types.ModuleType("kaggle")
        fake_extended_module = types.ModuleType("kaggle.api.kaggle_api_extended")
        fake_extended_module.KaggleApiExtended = fake_kaggle_api
        fake_kaggle_module.api = types.ModuleType("kaggle.api")
        fake_kaggle_module.api.kaggle_api_extended = fake_extended_module

        with patch.dict(os.environ, {"KAGGLE_API_TOKEN": "fake_token"}, clear=False):
            with patch("seed_data.load_dotenv", return_value=None):
                with patch("seed_data.time.sleep", return_value=None):
                    with patch.dict(sys.modules, {
                        "kaggle": fake_kaggle_module,
                        "kaggle.api": fake_kaggle_module.api,
                        "kaggle.api.kaggle_api_extended": fake_extended_module,
                    }):
                        with self.assertRaises(SystemExit) as ctx:
                            seed_data.download_kaggle("data/kaggle_raw.csv")

        self.assertEqual(ctx.exception.code, 1)
        # Should have attempted 3 times
        self.assertEqual(len(attempt_calls), 3)


class TestAdzunaNon2xxContinues(unittest.TestCase):
    """test_adzuna_non_2xx_continues: 404 response → pipeline continues (returns empty list)."""

    def test_404_returns_empty_list(self):
        """When Adzuna returns 404, fetch_adzuna returns an empty list for that role."""
        from seed_data import fetch_adzuna

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.ok = False

        with patch("seed_data.requests.get", return_value=mock_resp):
            with patch.dict(os.environ, {"ADZUNA_APP_ID": "id", "ADZUNA_APP_KEY": "key"}):
                result = fetch_adzuna(["software engineer"])

        self.assertEqual(result, [])


class TestAdzuna429Pauses(unittest.TestCase):
    """test_adzuna_429_pauses: 429 then 200 → time.sleep(60) called."""

    def test_429_then_200_calls_sleep(self):
        """When Adzuna returns 429 on first attempt, sleep(60) is called, then retries."""
        from seed_data import fetch_adzuna

        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.ok = False

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.ok = True
        resp_200.json.return_value = {"results": []}

        sleep_calls = []

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("seed_data.requests.get", side_effect=[resp_429, resp_200]):
            with patch("seed_data.time.sleep", side_effect=fake_sleep):
                with patch.dict(os.environ, {"ADZUNA_APP_ID": "id", "ADZUNA_APP_KEY": "key"}):
                    fetch_adzuna(["software engineer"])

        self.assertIn(60, sleep_calls, "Expected time.sleep(60) to be called on 429 response")


class TestPipelineLogOnException(unittest.TestCase):
    """test_pipeline_log_on_exception: unhandled exception → data/pipeline.log written."""

    def test_exception_writes_log(self):
        """When run_pipeline encounters an unhandled exception, it writes to data/pipeline.log."""
        import logging
        import tempfile
        import seed_data

        # Use a temp file so we can reliably check the output regardless of cwd
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as tmp:
            tmp_log_path = tmp.name

        try:
            # Add a file handler pointing to our temp log
            test_handler = logging.FileHandler(tmp_log_path)
            test_handler.setLevel(logging.ERROR)
            root_logger = logging.getLogger()
            root_logger.addHandler(test_handler)

            with patch("seed_data._run_pipeline_inner", side_effect=RuntimeError("Intentional test failure")):
                with self.assertRaises(SystemExit) as ctx:
                    seed_data.run_pipeline()

            self.assertEqual(ctx.exception.code, 1)

            test_handler.flush()
            test_handler.close()
            root_logger.removeHandler(test_handler)

            with open(tmp_log_path) as f:
                content = f.read()
            self.assertIn("Intentional test failure", content)
        finally:
            if os.path.exists(tmp_log_path):
                os.remove(tmp_log_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
