import json
import logging
from datetime import datetime

from bs4 import BeautifulSoup
from starlette.status import HTTP_200_OK

from SvenBot import utility
from SvenBot.config import REPO_URL, STEAM_URL, settings
from SvenBot.models import ResponseData

gunicorn_logger = logging.getLogger("gunicorn.error")


async def recruit_task() -> ResponseData:
    gunicorn_logger.info("Recruit task")
    return await utility.send_message(
        settings.STAFF_CHANNEL,
        f"<@&{settings.ADMIN_ROLE}> Post recruitment on <https://www.reddit.com/r/FindAUnit>",
        ["roles"],
    )


async def a3sync_task() -> ResponseData | None:
    r = await utility.get([HTTP_200_OK], f"{REPO_URL}/repo")
    repo_info = r.json()

    with open("revision.json") as f:
        revision = json.load(f)

    if repo_info["revision"] != revision["revision"]:
        r = await utility.get([HTTP_200_OK], f"{REPO_URL}/changelog")
        changelogs = r.json()["list"]

        new_repo_size = round((float(repo_info["totalFilesSize"]) / 1000000000), 2)
        update_post = f"```md\n# The A3Sync repo has changed #\n\n[{new_repo_size} GB]\n```\n"
        for changelog in changelogs:
            if changelog["revision"] > revision["revision"]:
                new = (
                    ""
                    if (len(changelog["newAddons"]) == 0)
                    else "< New >\n{}".format("\n".join(changelog["newAddons"]))
                )
                deleted = (
                    ""
                    if (len(changelog["deletedAddons"]) == 0)
                    else "\n\n< Deleted >\n{}".format("\n".join(changelog["deletedAddons"]))
                )
                updated = (
                    ""
                    if (len(changelog["updatedAddons"]) == 0)
                    else "\n\n< Updated >\n{}".format("\n".join(changelog["updatedAddons"]))
                )
                if len(new + deleted + updated) > 0:
                    update_post += f"```md\n{new}{deleted}{updated}\n```\n"

        revision["revision"] = changelog["revision"]

        with open("revision.json", "w") as f:
            json.dump(revision, f)

        return await utility.send_message(settings.ANNOUNCE_CHANNEL, update_post)
    return None


async def steam_task() -> ResponseData | None:
    with open("steam_timestamp.json") as f:
        steam_timestamp = json.load(f)

    mods = set(await get_steam_mods(settings.STEAM_MODLIST))
    data = {"itemcount": len(mods)}
    for i, mod in enumerate(mods):
        data[f"publishedfileids[{i}]"] = mod

    r = await utility.post([HTTP_200_OK], f"{STEAM_URL}/GetPublishedFileDetails/v1/", data=data, headers=None)

    update_post = ""
    now = datetime.utcnow().timestamp()
    last_checked = steam_timestamp["last_checked"]

    for mod in r.json()["response"]["publishedfiledetails"]:
        mod_id = mod["publishedfileid"]
        time_updated = mod.get("time_updated")
        if not time_updated:
            continue

        if last_checked <= time_updated <= now:
            changelog_url = f"https://steamcommunity.com/sharedfiles/filedetails/changelog/{mod_id}"
            update_post += f"**{mod['title']}** has released a new version\n<{changelog_url}>\n"

            try:
                changelog = await get_steam_changelog(changelog_url)
            except Exception as e:
                gunicorn_logger.error(f"Error retrieving changelog for {mod_id}:\n{e}")
                changelog = "Error retrieving changelog"

            update_post += f"```\n{changelog}```\n"

    steam_timestamp["last_checked"] = now
    with open("steam_timestamp.json", "w") as f:
        json.dump(steam_timestamp, f)

    if update_post:
        return await utility.send_message(
            settings.STAFF_CHANNEL, f"<@&{settings.ADMIN_ROLE}>\n{update_post}", ["roles"]
        )
    return None


async def get_steam_mods(collection: int) -> list[str]:
    data = {"collectioncount": 1, "publishedfileids[0]": collection}
    mods: list[str] = []

    r = await utility.post([HTTP_200_OK], f"{STEAM_URL}/GetCollectionDetails/v1/", data=data, headers=None)
    response = r.json()

    for collection in response["response"]["collectiondetails"]:
        for child in collection["children"]:
            if child["filetype"] == 0:
                mods.append(child["publishedfileid"])
            elif child["filetype"] == 2:
                mods += await get_steam_mods(child["publishedfileid"])

    return mods


async def get_steam_changelog(changelog_url: str) -> str:
    r = await utility.get([HTTP_200_OK], changelog_url, headers=None)
    soup = BeautifulSoup(r.text, features="html.parser")
    headline = soup.find("div", {"class": "changelog headline"})

    return headline.findNext("p").get_text(separator="\n")
