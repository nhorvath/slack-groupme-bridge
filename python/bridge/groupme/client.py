import mimetypes

import requests

from bridge.models import GroupMeBotMessage

GROUPME_BOT_POST_URL = "https://api.groupme.com/v3/bots/post"
GROUPME_IMAGE_UPLOAD_URL = "https://image.groupme.com/pictures"


def send_message(msg: GroupMeBotMessage) -> None:
    resp = requests.post(GROUPME_BOT_POST_URL, json=msg.to_dict())
    resp.raise_for_status()


def upload_picture(filename: str, data: bytes, access_key: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)
    if content_type is None:
        content_type = "application/octet-stream"
    resp = requests.post(
        f"{GROUPME_IMAGE_UPLOAD_URL}?token={access_key}",
        data=data,
        headers={"Content-Type": content_type},
    )
    resp.raise_for_status()
    return resp.json()["payload"]["url"]
