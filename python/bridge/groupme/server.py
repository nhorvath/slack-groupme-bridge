import logging
import traceback
from typing import Optional

from flask import Flask, request

from bridge.models import GroupMeWebhook, GroupMeAttachmentImage, SlackBotMessage

logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

_config = None
_slack_client = None


def init(config, slack_client) -> None:
    global _config, _slack_client
    _config = config
    _slack_client = slack_client


def _parse_webhook(data: dict) -> GroupMeWebhook:
    attachments = [
        GroupMeAttachmentImage(url=a["url"])
        for a in data.get("attachments", [])
        if a.get("type") == "image"
    ]
    return GroupMeWebhook(
        name=data.get("name", ""),
        sender_type=data.get("sender_type", ""),
        sender_id=data.get("sender_id", ""),
        group_id=data.get("group_id", ""),
        text=data.get("text") or "",
        avatar_url=data.get("avatar_url") or None,
        attachments=attachments,
    )


def _build_response(webhook: GroupMeWebhook) -> Optional[SlackBotMessage]:
    pair = _config.pairs_by_groupme_group.get(webhook.group_id)
    if pair is None:
        return None

    if webhook.sender_type == "bot":
        return None

    image_urls = [a.url for a in webhook.attachments]
    parts = [webhook.text] + image_urls
    final_text = "\n".join(p for p in parts if p)
    if not final_text:
        return None

    return SlackBotMessage(
        channel=pair.slack_channel_id,
        text=final_text,
        username=webhook.name,
        icon_url=webhook.avatar_url,
    )


@flask_app.route("/group-me", methods=["POST"])
def groupme_webhook():
    try:
        data = request.get_json(force=True)
        webhook = _parse_webhook(data)
        msg = _build_response(webhook)
        if msg is not None:
            _slack_client.send_message(msg)
    except Exception:
        logger.exception("Error handling GroupMe webhook")
        try:
            import sentry_sdk
            sentry_sdk.capture_exception()
        except Exception:
            pass
    return "", 200


def run_server() -> None:
    flask_app.run(host="0.0.0.0", port=5000, threaded=True)
