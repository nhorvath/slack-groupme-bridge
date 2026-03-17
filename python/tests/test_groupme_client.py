from unittest.mock import MagicMock, patch

from bridge.groupme.client import send_message, upload_picture
from bridge.models import GroupMeBotMessage


class TestSendMessage:
    @patch("bridge.groupme.client.requests.post")
    def test_posts_message_fields(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()
        send_message(GroupMeBotMessage(bot_id="b1", text="hi", token="tok"))
        payload = mock_post.call_args[1]["json"]
        assert payload["bot_id"] == "b1"
        assert payload["text"] == "hi"
        assert payload["token"] == "tok"

    @patch("bridge.groupme.client.requests.post")
    def test_posts_to_correct_url(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()
        send_message(GroupMeBotMessage(bot_id="b1", text="hi", token="tok"))
        url = mock_post.call_args[0][0]
        assert "bots/post" in url


class TestUploadPicture:
    @patch("bridge.groupme.client.requests.post")
    def test_returns_image_url(self, mock_post):
        mock_post.return_value.json.return_value = {"payload": {"url": "http://i.groupme.com/pic.jpg"}}
        mock_post.return_value.raise_for_status = MagicMock()
        url = upload_picture("image.jpg", b"data", "tok")
        assert url == "http://i.groupme.com/pic.jpg"

    @patch("bridge.groupme.client.requests.post")
    def test_token_included_in_request(self, mock_post):
        mock_post.return_value.json.return_value = {"payload": {"url": "http://x"}}
        mock_post.return_value.raise_for_status = MagicMock()
        upload_picture("img.png", b"d", "mytoken")
        url = mock_post.call_args[0][0]
        assert "mytoken" in url

    @patch("bridge.groupme.client.requests.post")
    def test_jpeg_content_type(self, mock_post):
        mock_post.return_value.json.return_value = {"payload": {"url": "http://x"}}
        mock_post.return_value.raise_for_status = MagicMock()
        upload_picture("photo.jpg", b"d", "tok")
        headers = mock_post.call_args[1]["headers"]
        assert headers["Content-Type"] == "image/jpeg"

    @patch("bridge.groupme.client.requests.post")
    def test_unknown_extension_falls_back_to_octet_stream(self, mock_post):
        mock_post.return_value.json.return_value = {"payload": {"url": "http://x"}}
        mock_post.return_value.raise_for_status = MagicMock()
        upload_picture("file.bin", b"d", "tok")
        headers = mock_post.call_args[1]["headers"]
        assert headers["Content-Type"] == "application/octet-stream"
