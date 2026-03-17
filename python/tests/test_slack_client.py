from unittest.mock import MagicMock, patch

import pytest

from bridge.models import SlackBotMessage
from bridge.slack.client import SlackApiClient


def _make_client():
    return SlackApiClient("xoxb-test")


class TestSendMessage:
    @patch("bridge.slack.client.requests.post")
    def test_posts_to_correct_url(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        mock_post.return_value.raise_for_status = MagicMock()
        _make_client().send_message(SlackBotMessage(channel="C1", text="hi", username="bot"))
        url = mock_post.call_args[0][0]
        assert "chat.postMessage" in url

    @patch("bridge.slack.client.requests.post")
    def test_sends_auth_header(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": True}
        mock_post.return_value.raise_for_status = MagicMock()
        _make_client().send_message(SlackBotMessage(channel="C1", text="hi", username="bot"))
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer xoxb-test"

    @patch("bridge.slack.client.requests.post")
    def test_api_error_raises(self, mock_post):
        mock_post.return_value.json.return_value = {"ok": False, "error": "channel_not_found"}
        mock_post.return_value.raise_for_status = MagicMock()
        with pytest.raises(RuntimeError, match="channel_not_found"):
            _make_client().send_message(SlackBotMessage(channel="C1", text="hi", username="bot"))


class TestGetUsername:
    @patch("bridge.slack.client.requests.get")
    def test_returns_display_name(self, mock_get):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "user": {"name": "alice", "profile": {"display_name": "Alice"}},
        }
        mock_get.return_value.raise_for_status = MagicMock()
        assert _make_client().get_username("U1") == "Alice"

    @patch("bridge.slack.client.requests.get")
    def test_falls_back_to_name_when_display_name_empty(self, mock_get):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "user": {"name": "alice", "profile": {"display_name": ""}},
        }
        mock_get.return_value.raise_for_status = MagicMock()
        assert _make_client().get_username("U1") == "alice"

    @patch("bridge.slack.client.requests.get")
    def test_result_is_cached(self, mock_get):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "user": {"name": "alice", "profile": {"display_name": "Alice"}},
        }
        mock_get.return_value.raise_for_status = MagicMock()
        client = _make_client()
        client.get_username("U1")
        client.get_username("U1")
        assert mock_get.call_count == 1

    @patch("bridge.slack.client.requests.get")
    def test_different_users_not_shared_in_cache(self, mock_get):
        mock_get.return_value.json.return_value = {
            "ok": True,
            "user": {"name": "alice", "profile": {"display_name": "Alice"}},
        }
        mock_get.return_value.raise_for_status = MagicMock()
        client = _make_client()
        client.get_username("U1")
        client.get_username("U2")
        assert mock_get.call_count == 2

    @patch("bridge.slack.client.requests.get")
    def test_api_error_raises(self, mock_get):
        mock_get.return_value.json.return_value = {"ok": False, "error": "user_not_found"}
        mock_get.return_value.raise_for_status = MagicMock()
        with pytest.raises(RuntimeError, match="user_not_found"):
            _make_client().get_username("U1")


class TestDownloadFile:
    @patch("bridge.slack.client.requests.get")
    def test_returns_content(self, mock_get):
        mock_get.return_value.content = b"filedata"
        mock_get.return_value.raise_for_status = MagicMock()
        result = _make_client().download_file("http://slack.com/file.jpg")
        assert result == b"filedata"

    @patch("bridge.slack.client.requests.get")
    def test_sends_auth_header(self, mock_get):
        mock_get.return_value.content = b""
        mock_get.return_value.raise_for_status = MagicMock()
        _make_client().download_file("http://slack.com/file.jpg")
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer xoxb-test"
