import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"


@dataclass
class ChannelPair:
    slack_channel_id: str
    groupme_bot_id: str
    groupme_group_id: str


@dataclass
class Config:
    groupme_access_key: str
    slack_access_key: str
    slack_app_token: str
    channel_pairs: list[ChannelPair]
    sentry_dsn: Optional[str]
    pairs_by_slack_channel: dict[str, ChannelPair]
    pairs_by_groupme_group: dict[str, ChannelPair]


def load_config() -> Config:
    load_dotenv(_ENV_FILE)

    def require(key: str) -> str:
        val = os.environ.get(key)
        if not val:
            raise RuntimeError(f"Missing required environment variable: {key}")
        return val

    groupme_access_key = require("GROUPME_ACCESS_KEY")
    slack_access_key = require("SLACK_ACCESS_KEY")
    slack_app_token = require("SLACK_APP_TOKEN")
    sentry_dsn = os.environ.get("SENTRY_DSN") or None

    raw_mappings = require("CHANNEL_MAPPINGS")
    try:
        mappings = json.loads(raw_mappings)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in CHANNEL_MAPPINGS: {e}") from e

    if not isinstance(mappings, list) or len(mappings) == 0:
        raise RuntimeError("CHANNEL_MAPPINGS must be a non-empty JSON array")

    channel_pairs = []
    for i, m in enumerate(mappings):
        for field in ("slack_channel_id", "groupme_bot_id", "groupme_group_id"):
            if field not in m:
                raise RuntimeError(f"CHANNEL_MAPPINGS[{i}] missing field: {field}")
        channel_pairs.append(ChannelPair(
            slack_channel_id=m["slack_channel_id"],
            groupme_bot_id=m["groupme_bot_id"],
            groupme_group_id=m["groupme_group_id"],
        ))

    pairs_by_slack_channel = {p.slack_channel_id: p for p in channel_pairs}
    pairs_by_groupme_group = {p.groupme_group_id: p for p in channel_pairs}

    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(dsn=sentry_dsn)

    return Config(
        groupme_access_key=groupme_access_key,
        slack_access_key=slack_access_key,
        slack_app_token=slack_app_token,
        channel_pairs=channel_pairs,
        sentry_dsn=sentry_dsn,
        pairs_by_slack_channel=pairs_by_slack_channel,
        pairs_by_groupme_group=pairs_by_groupme_group,
    )
