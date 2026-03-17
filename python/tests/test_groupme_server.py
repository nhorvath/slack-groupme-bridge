from unittest.mock import MagicMock

import pytest

from bridge.config import ChannelPair, Config
from bridge.groupme import server as groupme_server
from bridge.models import GroupMeAttachmentImage, GroupMeWebhook


def _make_config(pairs=None):
    if pairs is None:
        pairs = [ChannelPair(slack_channel_id="C1", groupme_bot_id="bot1", groupme_group_id="grp1")]
    return Config(
        groupme_access_key="gm-key",
        slack_access_key="xoxb-test",
        slack_app_token="xapp-test",
        channel_pairs=pairs,
        sentry_dsn=None,
        pairs_by_slack_channel={p.slack_channel_id: p for p in pairs},
        pairs_by_groupme_group={p.groupme_group_id: p for p in pairs},
    )


class TestParseWebhook:
    def test_basic_fields(self):
        data = {
            "name": "Alice",
            "sender_type": "user",
            "sender_id": "u1",
            "group_id": "grp1",
            "text": "hello",
            "avatar_url": "http://avatar",
            "attachments": [],
        }
        wh = groupme_server._parse_webhook(data)
        assert wh.name == "Alice"
        assert wh.text == "hello"
        assert wh.group_id == "grp1"
        assert wh.avatar_url == "http://avatar"
        assert wh.attachments == []

    def test_image_attachments_parsed(self):
        data = {
            "name": "Bob",
            "sender_type": "user",
            "sender_id": "u2",
            "group_id": "grp1",
            "text": "",
            "avatar_url": None,
            "attachments": [
                {"type": "image", "url": "http://img.jpg"},
                {"type": "location", "url": "should-be-ignored"},
            ],
        }
        wh = groupme_server._parse_webhook(data)
        assert len(wh.attachments) == 1
        assert wh.attachments[0].url == "http://img.jpg"

    def test_missing_fields_use_defaults(self):
        wh = groupme_server._parse_webhook({})
        assert wh.name == ""
        assert wh.text == ""
        assert wh.avatar_url is None
        assert wh.attachments == []

    def test_null_text_becomes_empty_string(self):
        wh = groupme_server._parse_webhook({"text": None})
        assert wh.text == ""


class TestBuildResponse:
    def setup_method(self):
        groupme_server._config = _make_config()

    def test_unknown_group_returns_none(self):
        wh = GroupMeWebhook(name="X", sender_type="user", sender_id="u1",
                            group_id="unknown", text="hi", avatar_url=None, attachments=[])
        assert groupme_server._build_response(wh) is None

    def test_bot_sender_returns_none(self):
        wh = GroupMeWebhook(name="Bot", sender_type="bot", sender_id="bot1",
                            group_id="grp1", text="hi", avatar_url=None, attachments=[])
        assert groupme_server._build_response(wh) is None

    def test_builds_correct_message(self):
        wh = GroupMeWebhook(name="Alice", sender_type="user", sender_id="u1",
                            group_id="grp1", text="hello", avatar_url="http://avatar", attachments=[])
        msg = groupme_server._build_response(wh)
        assert msg is not None
        assert msg.channel == "C1"
        assert msg.text == "hello"
        assert msg.username == "Alice"
        assert msg.icon_url == "http://avatar"

    def test_image_attachment_appended_to_text(self):
        wh = GroupMeWebhook(name="Alice", sender_type="user", sender_id="u1",
                            group_id="grp1", text="check this",
                            avatar_url=None,
                            attachments=[GroupMeAttachmentImage(url="http://img.jpg")])
        msg = groupme_server._build_response(wh)
        assert "http://img.jpg" in msg.text

    def test_image_only_no_text(self):
        wh = GroupMeWebhook(name="Alice", sender_type="user", sender_id="u1",
                            group_id="grp1", text="",
                            avatar_url=None,
                            attachments=[GroupMeAttachmentImage(url="http://img.jpg")])
        msg = groupme_server._build_response(wh)
        assert msg is not None
        assert msg.text == "http://img.jpg"

    def test_empty_text_no_attachments_returns_none(self):
        wh = GroupMeWebhook(name="Alice", sender_type="user", sender_id="u1",
                            group_id="grp1", text="", avatar_url=None, attachments=[])
        assert groupme_server._build_response(wh) is None


class TestWebhookEndpoint:
    def setup_method(self):
        self.mock_slack = MagicMock()
        groupme_server.init(_make_config(), self.mock_slack)
        self.client = groupme_server.flask_app.test_client()

    def _post(self, payload):
        return self.client.post("/group-me", json=payload)

    def test_valid_message_forwarded_to_slack(self):
        resp = self._post({
            "name": "Alice", "sender_type": "user", "sender_id": "u1",
            "group_id": "grp1", "text": "hello", "attachments": [],
        })
        assert resp.status_code == 200
        self.mock_slack.send_message.assert_called_once()
        sent = self.mock_slack.send_message.call_args[0][0]
        assert sent.text == "hello"
        assert sent.username == "Alice"
        assert sent.channel == "C1"

    def test_bot_message_not_forwarded(self):
        resp = self._post({
            "name": "Bot", "sender_type": "bot", "sender_id": "bot1",
            "group_id": "grp1", "text": "ignored", "attachments": [],
        })
        assert resp.status_code == 200
        self.mock_slack.send_message.assert_not_called()

    def test_unknown_group_not_forwarded(self):
        resp = self._post({
            "name": "Alice", "sender_type": "user", "sender_id": "u1",
            "group_id": "unknown", "text": "hello", "attachments": [],
        })
        assert resp.status_code == 200
        self.mock_slack.send_message.assert_not_called()

    def test_always_returns_200(self):
        # Even malformed payloads return 200 to avoid GroupMe retries
        resp = self.client.post("/group-me", data="not-json", content_type="text/plain")
        assert resp.status_code == 200
