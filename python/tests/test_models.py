from bridge.models import GroupMeBotMessage, SlackBotMessage


class TestSlackBotMessageToDict:
    def test_includes_icon_url_when_set(self):
        msg = SlackBotMessage(channel="C1", text="hi", username="bot", icon_url="http://icon")
        d = msg.to_dict()
        assert d["channel"] == "C1"
        assert d["text"] == "hi"
        assert d["username"] == "bot"
        assert d["icon_url"] == "http://icon"

    def test_omits_icon_url_when_none(self):
        msg = SlackBotMessage(channel="C1", text="hi", username="bot")
        assert "icon_url" not in msg.to_dict()

    def test_defaults(self):
        msg = SlackBotMessage(channel="C1", text="hi", username="bot")
        d = msg.to_dict()
        assert d["unfurl_links"] is True
        assert d["unfurl_media"] is True
        assert d["link_names"] is False


class TestGroupMeBotMessageToDict:
    def test_includes_picture_url_when_set(self):
        msg = GroupMeBotMessage(bot_id="b1", text="hi", token="tok", picture_url="http://pic")
        d = msg.to_dict()
        assert d["bot_id"] == "b1"
        assert d["text"] == "hi"
        assert d["token"] == "tok"
        assert d["picture_url"] == "http://pic"

    def test_omits_picture_url_when_none(self):
        msg = GroupMeBotMessage(bot_id="b1", text="hi", token="tok")
        assert "picture_url" not in msg.to_dict()
