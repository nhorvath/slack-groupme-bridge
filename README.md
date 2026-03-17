# slack-groupme-bridge

A messaging bridge connecting a GroupMe Group with a Slack Channel.

As part of an attempt to migrate my friends' group message from GroupMe to Slack I'm building this. The hope is this
will make it possible for a portion of the group to migrate to Slack without fragmenting the conversation. Then we can
peer pressure the hold outs 😏.



## Adding Channel Mappings

Channel mappings are configured via the `CHANNEL_MAPPINGS` environment variable in `.env.local` as a JSON array. Each entry bridges one Slack channel to one GroupMe group.

```json
CHANNEL_MAPPINGS=[
  {
    "slack_channel_id": "C012AB3CD",
    "groupme_bot_id": "abc1234567890",
    "groupme_group_id": "12345678"
  }
]
```

### Finding the IDs

**Slack channel ID (`slack_channel_id`)**
- Open Slack and go to the channel
- Click the channel name at the top to open channel details
- Scroll to the bottom — the channel ID (starts with `C`) is displayed there
- Alternatively, right-click the channel in the sidebar → "Copy link" — the ID is the last path segment

**GroupMe group ID (`groupme_group_id`)**
- Open GroupMe in a browser and navigate to the group
- The group ID is in the URL: `https://web.groupme.com/groups/12345678`

**GroupMe bot ID (`groupme_bot_id`)**
- Go to [dev.groupme.com/bots](https://dev.groupme.com/bots) and create a new bot for the group
- Set the callback URL to `https://your-host/group-me`
- After creation, copy the **Bot ID** shown on that page
- Note: the Bot ID is different from the access token

## Local Dev
To test small changes, use the repl:

```bash
stack repl
```

To build for prod and run a production build locally (via docker):

```bash
./linux-build.sh && docker-compose up --build
```

## Deployment

App deployment:
```bash
./linux-build.sh && ./upload-to-ecr.sh
```

Nginx deployment:
```bash
./nginx-upload-to-ecr.sh
```