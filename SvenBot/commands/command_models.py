from pydantic import BaseModel

from SvenBot.models import OptionType


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
    default_permission: bool = True
    options: list[OptionDefinition] | None
    choices: list[Choice] | None


ping = CommandDefinition(
    name="ping",
    description="Ping!"
)

addrole = CommandDefinition(
    name="addrole",
    description="Add a new role",
    default_permission=False,
    options=[
        OptionDefinition(
            name="name",
            description="Name",
            type=OptionType.STRING,
        )
    ]
)

cointoss = CommandDefinition(
    name="cointoss",
    description="Flip a coin"
)

removerole = CommandDefinition(
    name="removerole",
    description="Remove an existing role",
    default_permission=False,
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        )
    ]
)

renamerole = CommandDefinition(
    name="renamerole",
    description="Rename an existing role",
    default_permission=False,
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
        )
    ]
)

members = CommandDefinition(
    name="members",
    description="Get a list of members in a role",
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        )
    ]
)

myroles = CommandDefinition(
    name="myroles",
    description="Get a list of roles you're in"
)

optime = CommandDefinition(
    name="optime",
    description="Time until optime",
    options=[
        OptionDefinition(
            name="modifier",
            description="Modifier",
            type=OptionType.INTEGER,
            required=False
        )
    ]
)

role = CommandDefinition(
    name="role",
    description="Join or leave a role",
    options=[
        OptionDefinition(
            name="role",
            description="Role",
            type=OptionType.ROLE,
        )
    ]
)

roles = CommandDefinition(
    name="roles",
    description="Get a list of roles you can join"
)

subscribe = CommandDefinition(
    name="subscribe",
    description="(Un)subscribe to mission notifications",
    options=[
        OptionDefinition(
            name="mission",
            description="The mission ID",
            type=OptionType.INTEGER
        )
    ]
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
                Choice(name="svenbot", value="TomBurch/SvenBot")
            ]
        ),
        OptionDefinition(
            name="title",
            description="Ticket title",
            type=OptionType.STRING,
        ),
        OptionDefinition(
            name="body",
            description="Ticket description",
            type=OptionType.STRING
        )
    ]
)
