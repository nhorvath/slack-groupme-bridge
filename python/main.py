import logging
import threading

from bridge.config import load_config
from bridge.groupme import client as groupme_client
from bridge.groupme import server as groupme_server
from bridge.slack.client import SlackApiClient
from bridge.slack.listener import SlackListener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def main():
    config = load_config()
    slack_api = SlackApiClient(config.slack_access_key)
    groupme_server.init(config, slack_api)
    listener = SlackListener(config, slack_api, groupme_client)
    socket_client = listener.start()
    threading.Thread(target=groupme_server.run_server, daemon=True).start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        socket_client.close()


if __name__ == "__main__":
    main()
