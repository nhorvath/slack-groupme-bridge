from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SlackMessage:
    channel: str
    text: str
    user: str


@dataclass
class SlackFileComment:
    comment: str
    user: str


@dataclass
class SlackFile:
    name: str
    url_private: str
    initial_comment: Optional[SlackFileComment]


@dataclass
class SlackFileShare:
    user: str
    channel: str
    file: SlackFile


@dataclass
class SlackBotMessage:
    channel: str
    text: str
    username: str
    icon_url: Optional[str] = None
    unfurl_links: bool = True
    unfurl_media: bool = True
    link_names: bool = False

    def to_dict(self) -> dict:
        d = {
            "channel": self.channel,
            "text": self.text,
            "username": self.username,
            "unfurl_links": self.unfurl_links,
            "unfurl_media": self.unfurl_media,
            "link_names": self.link_names,
        }
        if self.icon_url is not None:
            d["icon_url"] = self.icon_url
        return d


@dataclass
class GroupMeAttachmentImage:
    url: str


@dataclass
class GroupMeWebhook:
    name: str
    sender_type: str
    sender_id: str
    group_id: str
    text: str
    avatar_url: Optional[str]
    attachments: list[GroupMeAttachmentImage]


@dataclass
class GroupMeBotMessage:
    bot_id: str
    text: str
    token: str
    picture_url: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "bot_id": self.bot_id,
            "text": self.text,
            "token": self.token,
        }
        if self.picture_url is not None:
            d["picture_url"] = self.picture_url
        return d
