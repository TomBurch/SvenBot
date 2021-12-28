from enum import IntEnum
from typing import Any, Optional, List

from pydantic import BaseModel


class InteractionResponseType(IntEnum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5


class ResponseData(BaseModel):
    tts: Optional[bool]
    content: Optional[str]
    embeds: Any
    allowed_mentions: Any
    flags: Optional[int]
    components: Any


class Response(BaseModel):
    type: InteractionResponseType
    data: Optional[ResponseData]


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
    bot: Optional[bool]
    system: Any
    mfa_enabled: Any
    locale: Any
    verified: Any
    email: Any
    flags: Any
    premium_type: Any
    public_flags: Any


class Member(BaseModel):
    user: Optional[User]
    nick: Optional[str]
    roles: Any
    joined_at: Any
    premium_since: Any
    deaf: Any
    mute: Any
    pending: Any
    permissions: Optional[str]


class Option(BaseModel):
    name: str
    type: OptionType
    value: Any
    options: Optional[List['Option']]


Option.update_forward_refs()


class Command(BaseModel):
    id: str
    name: str
    resolved: Any
    options: Optional[List[Option]]
    custom_id: Any
    component_type: Any


class Interaction(BaseModel):
    id: str
    application_id: str
    type: InteractionType
    data: Optional[Command]
    guild_id: Optional[str]
    channel_id: Optional[str]
    member: Optional[Member]
    user: Optional[User]
    token: str
    version: int
    message: Any
