from pydantic import BaseModel

from SvenBot.models import OptionType

MANAGE_GUILD_PERMISSION = str(1 << 5)


class Choice(BaseModel):
    name: str
    value: str


class OptionDefinition(BaseModel):
    name: str
    description: str
    type: OptionType
    required: bool = True


class CommandDefinition(BaseModel):
    name: str
    description: str
    default_member_permissions: str | None = None
    options: list[OptionDefinition] | None
    choices: list[Choice] | None


ping = CommandDefinition(
    name="ping",
    description="Ping!",
)

addrole = CommandDefinition(
    name="addrole",
    description="Add a new role",
    default_member_permissions=MANAGE_GUILD_PERMISSION,
    options=[
        OptionDefinition(
            name="name",
            description="Name",
            type=OptionType.STRING,
        ),
    ],
)

cointoss = CommandDefinition(
    name="cointoss",
    description="Flip a coin",
)

d20 = CommandDefinition(
    name="d20",
    description="Roll dice with Avrae",
    options=[
        OptionDefinition(
            name="options",
            description="Options",
            type=OptionType.STRING,
        ),
    ],
)

removerole = CommandDefinition(
    name="removerole",
    description="Remove an existing role",
    default_member_permissions=MANAGE_GUILD_PERMISSION,
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        ),
    ],
)

renamemap = CommandDefinition(
    name="renamemap",
    description="Rename a map on ARCHUB",
    default_member_permissions=MANAGE_GUILD_PERMISSION,
    options=[
        OptionDefinition(
            name="old_name",
            description="Old name",
            type=OptionType.STRING,
        ),
        OptionDefinition(
            name="new_name",
            description="New name",
            type=OptionType.STRING,
        ),
    ],
)

renamerole = CommandDefinition(
    name="renamerole",
    description="Rename an existing role",
    default_member_permissions=MANAGE_GUILD_PERMISSION,
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        ),
        OptionDefinition(
            name="name",
            description="New name",
            type=OptionType.STRING,
        ),
    ],
)

maps = CommandDefinition(
    name="maps",
    description="Get a list of maps on ARCHUB",
)

members = CommandDefinition(
    name="members",
    description="Get a list of members in a role",
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        ),
    ],
)

myroles = CommandDefinition(
    name="myroles",
    description="Get a list of roles you're in",
)

optime = CommandDefinition(
    name="optime",
    description="Time until optime",
    options=[
        OptionDefinition(
            name="modifier",
            description="Modifier",
            type=OptionType.INTEGER,
            required=False,
        ),
    ],
)

role = CommandDefinition(
    name="role",
    description="Join or leave a role",
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        ),
    ],
)

roles = CommandDefinition(
    name="roles",
    description="Get a list of roles you can join",
)

subscribe = CommandDefinition(
    name="subscribe",
    description="(Un)subscribe to mission notifications",
    options=[
        OptionDefinition(
            name="mission",
            description="The mission ID",
            type=OptionType.INTEGER,
        ),
    ],
)

ticket = CommandDefinition(
    name="ticket",
    description="Create a github ticket",
    options=[
        OptionDefinition(
            name="repo",
            description="Target repo",
            type=OptionType.STRING,
            choices=[
                Choice(name="archub", value="ARCOMM/ARCHUB"),
                Choice(name="arc_misc", value="ARCOMM/arc_misc"),
                Choice(name="arcmt", value="ARCOMM/ARCMT"),
                Choice(name="svenbot", value="TomBurch/SvenBot"),
            ],
        ),
        OptionDefinition(
            name="title",
            description="Ticket title",
            type=OptionType.STRING,
        ),
        OptionDefinition(
            name="body",
            description="Ticket description",
            type=OptionType.STRING,
        ),
    ],
)
