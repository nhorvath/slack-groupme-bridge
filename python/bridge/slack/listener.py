import logging
from concurrent.futures import ThreadPoolExecutor

from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

from bridge import groupme
from bridge.models import GroupMeBotMessage

logger = logging.getLogger(__name__)


class SlackListener:
    def __init__(self, config, slack_api_client, groupme_client):
        self._config = config
        self._slack_api = slack_api_client
        self._groupme = groupme_client

    def start(self) -> SocketModeClient:
        client = SocketModeClient(
            app_token=self._config.slack_app_token,
            web_client=None,
        )
        client.socket_mode_request_listeners.append(self._handle_request)
        client.connect()
        return client

    def _handle_request(self, client: SocketModeClient, req: SocketModeRequest) -> None:
        client.send_socket_mode_response(
            SocketModeResponse(envelope_id=req.envelope_id)
        )
        if req.type != "events_api":
            return
        try:
            event = req.payload.get("event", {})
            event_type = event.get("type")
            subtype = event.get("subtype")

            if event_type == "message" and subtype == "file_share":
                self._handle_file_share(event)
            elif event_type == "message" and subtype is None:
                self._handle_message(event)
        except Exception:
            logger.exception("Error handling Slack event")
            try:
                import sentry_sdk
                sentry_sdk.capture_exception()
            except Exception:
                pass

    def _handle_message(self, event: dict) -> None:
        channel = event.get("channel", "")
        pair = self._config.pairs_by_slack_channel.get(channel)
        if pair is None:
            return

        user_id = event.get("user", "")
        text = event.get("text", "")
        username = self._slack_api.get_username(user_id)

        msg = GroupMeBotMessage(
            bot_id=pair.groupme_bot_id,
            text=f"{username}: {text}",
            token=self._config.groupme_access_key,
        )
        self._groupme.send_message(msg)

    def _handle_file_share(self, event: dict) -> None:
        channel = event.get("channel", "")
        pair = self._config.pairs_by_slack_channel.get(channel)
        if pair is None:
            return

        user_id = event.get("user", "")
        files = event.get("files", [])
        if not files:
            return
        slack_file = files[0]

        file_url = slack_file.get("url_private", "")
        filename = slack_file.get("name", "file")
        comment = None
        initial_comment = slack_file.get("initial_comment")
        if initial_comment:
            comment = initial_comment.get("comment")

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_img = executor.submit(
                self._transfer_image, file_url, filename
            )
            future_user = executor.submit(self._slack_api.get_username, user_id)

            groupme_image_url = future_img.result()
            username = future_user.result()

        text = f"{username}: {comment}" if comment else f"{username}: "
        msg = GroupMeBotMessage(
            bot_id=pair.groupme_bot_id,
            text=text,
            token=self._config.groupme_access_key,
            picture_url=groupme_image_url,
        )
        self._groupme.send_message(msg)

    def _transfer_image(self, url: str, filename: str) -> str:
        data = self._slack_api.download_file(url)
        return self._groupme.upload_picture(filename, data, self._config.groupme_access_key)
