import json
import os
from unittest.mock import patch

import pytest

from bridge.config import ChannelPair, load_config


def _env(**overrides):
    base = {
        "SLACK_APP_TOKEN": "xapp-test",
        "SLACK_ACCESS_KEY": "xoxb-test",
        "GROUPME_ACCESS_KEY": "gm-key",
        "CHANNEL_MAPPINGS": json.dumps([
            {"slack_channel_id": "C1", "groupme_bot_id": "b1", "groupme_group_id": "g1"},
        ]),
    }
    base.update(overrides)
    return base


@patch("bridge.config.load_dotenv")
def test_valid_config(mock_ld):
    with patch.dict(os.environ, _env(), clear=True):
        config = load_config()

    assert config.slack_app_token == "xapp-test"
    assert config.slack_access_key == "xoxb-test"
    assert config.groupme_access_key == "gm-key"
    assert config.sentry_dsn is None
    assert len(config.channel_pairs) == 1
    pair = config.channel_pairs[0]
    assert pair.slack_channel_id == "C1"
    assert pair.groupme_bot_id == "b1"
    assert pair.groupme_group_id == "g1"
    assert config.pairs_by_slack_channel["C1"] is pair
    assert config.pairs_by_groupme_group["g1"] is pair


@patch("bridge.config.load_dotenv")
def test_multiple_channel_pairs(mock_ld):
    mappings = json.dumps([
        {"slack_channel_id": "C1", "groupme_bot_id": "b1", "groupme_group_id": "g1"},
        {"slack_channel_id": "C2", "groupme_bot_id": "b2", "groupme_group_id": "g2"},
    ])
    with patch.dict(os.environ, _env(CHANNEL_MAPPINGS=mappings), clear=True):
        config = load_config()

    assert len(config.channel_pairs) == 2
    assert "C1" in config.pairs_by_slack_channel
    assert "C2" in config.pairs_by_slack_channel
    assert "g1" in config.pairs_by_groupme_group
    assert "g2" in config.pairs_by_groupme_group


@pytest.mark.parametrize("missing_key", ["SLACK_APP_TOKEN", "SLACK_ACCESS_KEY", "GROUPME_ACCESS_KEY", "CHANNEL_MAPPINGS"])
@patch("bridge.config.load_dotenv")
def test_missing_required_var(mock_ld, missing_key):
    env = _env()
    del env[missing_key]
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(RuntimeError, match=missing_key):
            load_config()


@patch("bridge.config.load_dotenv")
def test_invalid_channel_mappings_json(mock_ld):
    with patch.dict(os.environ, _env(CHANNEL_MAPPINGS="not-json"), clear=True):
        with pytest.raises(RuntimeError, match="Invalid JSON"):
            load_config()


@patch("bridge.config.load_dotenv")
def test_empty_channel_mappings(mock_ld):
    with patch.dict(os.environ, _env(CHANNEL_MAPPINGS="[]"), clear=True):
        with pytest.raises(RuntimeError, match="non-empty"):
            load_config()


@patch("bridge.config.load_dotenv")
def test_missing_mapping_field(mock_ld):
    bad = json.dumps([{"slack_channel_id": "C1", "groupme_bot_id": "b1"}])
    with patch.dict(os.environ, _env(CHANNEL_MAPPINGS=bad), clear=True):
        with pytest.raises(RuntimeError, match="groupme_group_id"):
            load_config()
