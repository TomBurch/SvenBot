from enum import IntEnum, Enum
from typing import Any, ForwardRef

from pydantic import BaseModel


class InteractionResponseType(IntEnum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5


class EmbedField(BaseModel):
    name: str
    value: str
    inline: bool = False


class Embed(BaseModel):
    title: str
    description: str
    color: int | None
    fields: list[EmbedField] | None


class ResponseData(BaseModel):
    tts: bool | None
    content: str | None
    embeds: list[Embed] | None
    allowed_mentions: Any
    flags: int | None
    components: Any


class Response(BaseModel):
    type: InteractionResponseType
    data: ResponseData | None


class InteractionType(IntEnum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3


class OptionType(IntEnum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9


class User(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Any
    bot: bool | None
    system: Any
    mfa_enabled: Any
    locale: Any
    verified: Any
    email: Any
    flags: Any
    premium_type: Any
    public_flags: Any


class Member(BaseModel):
    user: User | None
    nick: str | None
    roles: Any
    joined_at: Any
    premium_since: Any
    deaf: Any
    mute: Any
    pending: Any
    permissions: str | None


Option = ForwardRef('Option')


class Option(BaseModel):
    name: str
    type: OptionType
    value: Any
    options: list[Option] | None


Option.update_forward_refs()


class Command(BaseModel):
    id: str
    name: str
    resolved: Any
    options: list[Option] | None
    custom_id: Any
    component_type: Any


class Interaction(BaseModel):
    id: str
    application_id: str
    type: InteractionType
    data: Command | None
    guild_id: str | None
    channel_id: str | None
    member: Member | None
    user: User | None
    token: str
    version: int
    message: Any


class SlackCalendarEvent(BaseModel):
    color: str
    pretext: str | None
    title: str | None
    text: str | None


class SlackEvent(BaseModel):
    type: str
    text: str
    attachments: list[SlackCalendarEvent] | None


class SlackNotificationType(str, Enum):
    VERIFICATION = "url_verification"
    CALLBACK = "event_callback"


class SlackNotification(BaseModel):
    token: str
    challenge: str | None
    type: SlackNotificationType
    event: SlackEvent | None
