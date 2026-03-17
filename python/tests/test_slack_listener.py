from unittest.mock import MagicMock

from bridge.config import ChannelPair, Config
from bridge.slack.listener import SlackListener


def _make_config():
    pair = ChannelPair(slack_channel_id="C1", groupme_bot_id="bot1", groupme_group_id="grp1")
    return Config(
        groupme_access_key="gm-key",
        slack_access_key="xoxb-test",
        slack_app_token="xapp-test",
        channel_pairs=[pair],
        sentry_dsn=None,
        pairs_by_slack_channel={"C1": pair},
        pairs_by_groupme_group={"grp1": pair},
    )


class TestHandleMessage:
    def setup_method(self):
        self.slack_api = MagicMock()
        self.groupme = MagicMock()
        self.listener = SlackListener(_make_config(), self.slack_api, self.groupme)
        self.slack_api.get_username.return_value = "Alice"

    def test_message_forwarded_to_groupme(self):
        self.listener._handle_message({"channel": "C1", "user": "U1", "text": "hello"})
        self.groupme.send_message.assert_called_once()
        sent = self.groupme.send_message.call_args[0][0]
        assert sent.bot_id == "bot1"
        assert sent.text == "Alice: hello"

    def test_username_fetched_by_user_id(self):
        self.listener._handle_message({"channel": "C1", "user": "U99", "text": "hi"})
        self.slack_api.get_username.assert_called_once_with("U99")

    def test_unknown_channel_ignored(self):
        self.listener._handle_message({"channel": "C_UNKNOWN", "user": "U1", "text": "hi"})
        self.groupme.send_message.assert_not_called()

    def test_groupme_token_set_correctly(self):
        self.listener._handle_message({"channel": "C1", "user": "U1", "text": "hi"})
        sent = self.groupme.send_message.call_args[0][0]
        assert sent.token == "gm-key"


class TestHandleFileShare:
    def setup_method(self):
        self.slack_api = MagicMock()
        self.groupme = MagicMock()
        self.listener = SlackListener(_make_config(), self.slack_api, self.groupme)
        self.slack_api.get_username.return_value = "Alice"
        self.slack_api.download_file.return_value = b"imagedata"
        self.groupme.upload_picture.return_value = "http://groupme.img/pic.jpg"

    def test_file_forwarded_with_picture_url(self):
        event = {
            "channel": "C1",
            "user": "U1",
            "files": [{"url_private": "http://slack.com/file.jpg", "name": "file.jpg"}],
        }
        self.listener._handle_file_share(event)
        self.groupme.send_message.assert_called_once()
        sent = self.groupme.send_message.call_args[0][0]
        assert sent.picture_url == "http://groupme.img/pic.jpg"
        assert "Alice" in sent.text

    def test_file_with_comment_included_in_text(self):
        event = {
            "channel": "C1",
            "user": "U1",
            "files": [{
                "url_private": "http://slack.com/file.jpg",
                "name": "file.jpg",
                "initial_comment": {"comment": "look at this"},
            }],
        }
        self.listener._handle_file_share(event)
        sent = self.groupme.send_message.call_args[0][0]
        assert "look at this" in sent.text

    def test_image_downloaded_and_reuploaded(self):
        event = {
            "channel": "C1",
            "user": "U1",
            "files": [{"url_private": "http://slack.com/img.png", "name": "img.png"}],
        }
        self.listener._handle_file_share(event)
        self.slack_api.download_file.assert_called_once_with("http://slack.com/img.png")
        self.groupme.upload_picture.assert_called_once_with("img.png", b"imagedata", "gm-key")

    def test_unknown_channel_ignored(self):
        event = {
            "channel": "C_UNKNOWN",
            "user": "U1",
            "files": [{"url_private": "http://f", "name": "f.jpg"}],
        }
        self.listener._handle_file_share(event)
        self.groupme.send_message.assert_not_called()

    def test_no_files_ignored(self):
        self.listener._handle_file_share({"channel": "C1", "user": "U1", "files": []})
        self.groupme.send_message.assert_not_called()
