from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    ARCHUB_TOKEN: str
    BOT_TOKEN: str
    CLIENT_ID: str
    PUBLIC_KEY: str
    GITHUB_TOKEN: str

    STEAM_MODLIST: int

    ANNOUNCE_CHANNEL: int
    OP_CHANNEL: int
    TEST_CHANNEL: int
    STAFF_CHANNEL: int

    ADMIN_ROLE: int
    MEMBER_ROLE: int
    RECRUIT_ROLE: int

    class Config:
        env_file = ".env"


settings = Settings()

EVENT_PINGS = {
    "main": [[settings.MEMBER_ROLE, settings.RECRUIT_ROLE], settings.OP_CHANNEL, 0x992D22],
    "recruit": [[settings.RECRUIT_ROLE], settings.OP_CHANNEL, 0x1F8B4C],
}

BASE_ARCHUB_URL = "https://arcomm.co.uk"
HUB_URL = f"{BASE_ARCHUB_URL}/hub"
ARCHUB_API = f"{BASE_ARCHUB_URL}/api/v1"
APP_URL = f"https://discord.com/api/v8/applications/{settings.CLIENT_ID}"
CHANNELS_URL = "https://discord.com/api/v8/channels"
GUILD_URL = "https://discord.com/api/v8/guilds"
REPO_URL = "https://events.arcomm.co.uk/api"
STEAM_URL = "https://api.steampowered.com/ISteamRemoteStorage"

DEFAULT_HEADERS = {
    "Authorization": f"Bot {settings.BOT_TOKEN}",
}
ARCHUB_HEADERS = {
    "Authorization": f"Bearer {settings.ARCHUB_TOKEN}",
}
GITHUB_HEADERS = {
    "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
}
