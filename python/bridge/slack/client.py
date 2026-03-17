import threading

import requests
from cachetools import TTLCache

from bridge.models import SlackBotMessage

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
SLACK_USERS_INFO_URL = "https://slack.com/api/users.info"


class SlackApiClient:
    def __init__(self, access_key: str):
        self._access_key = access_key
        self._username_cache: TTLCache = TTLCache(maxsize=100, ttl=100)
        self._cache_lock = threading.Lock()

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_key}"}

    def send_message(self, msg: SlackBotMessage) -> None:
        resp = requests.post(
            SLACK_POST_MESSAGE_URL,
            json=msg.to_dict(),
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"Slack API error: {body.get('error')}")

    def get_username(self, user_id: str) -> str:
        with self._cache_lock:
            if user_id in self._username_cache:
                return self._username_cache[user_id]

        resp = requests.get(
            SLACK_USERS_INFO_URL,
            params={"user": user_id},
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"Slack API error: {body.get('error')}")

        profile = body["user"]["profile"]
        name = profile.get("display_name") or profile.get("real_name") or body["user"]["name"]

        with self._cache_lock:
            self._username_cache[user_id] = name

        return name

    def download_file(self, url: str) -> bytes:
        resp = requests.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.content
