import json
import logging
from datetime import datetime

from bs4 import BeautifulSoup
from starlette.status import HTTP_200_OK

from SvenBot import utility
from SvenBot.config import REPO_URL, STEAM_URL, settings

gunicorn_logger = logging.getLogger("gunicorn.error")


async def recruit_task():
    gunicorn_logger.info("Recruit task")
    return await utility.sendMessage(
        settings.STAFF_CHANNEL,
        f"<@&{settings.ADMIN_ROLE}> Post recruitment on <https://www.reddit.com/r/FindAUnit>",
        ["roles"],
    )


async def a3sync_task():
    r = await utility.get([HTTP_200_OK], f"{REPO_URL}/repo")
    repoInfo = r.json()

    with open("revision.json") as f:
        revision = json.load(f)

    if repoInfo["revision"] != revision["revision"]:
        r = await utility.get([HTTP_200_OK], f"{REPO_URL}/changelog")
        changelogs = r.json()["list"]

        newRepoSize = round((float(repoInfo["totalFilesSize"]) / 1000000000), 2)
        updatePost = f"```md\n# The A3Sync repo has changed #\n\n[{newRepoSize} GB]\n```\n"
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
                    updatePost += f"```md\n{new}{deleted}{updated}\n```\n"

        revision["revision"] = changelog["revision"]

        with open("revision.json", "w") as f:
            json.dump(revision, f)

        return await utility.sendMessage(settings.ANNOUNCE_CHANNEL, updatePost)
    return None


async def steam_task():
    with open("steam_timestamp.json") as f:
        steam_timestamp = json.load(f)

    mods = set(await getSteamMods(settings.STEAM_MODLIST))
    data = {"itemcount": len(mods)}
    for i, mod in enumerate(mods):
        data[f"publishedfileids[{i}]"] = mod

    r = await utility.post([HTTP_200_OK], f"{STEAM_URL}/GetPublishedFileDetails/v1/", data=data, headers=None)

    updatePost = ""
    now = datetime.utcnow().timestamp()
    lastChecked = steam_timestamp["last_checked"]

    for mod in r.json()["response"]["publishedfiledetails"]:
        modId = mod["publishedfileid"]
        timeUpdated = mod.get("time_updated")
        if not timeUpdated:
            continue

        if lastChecked <= timeUpdated <= now:
            changelogUrl = f"https://steamcommunity.com/sharedfiles/filedetails/changelog/{modId}"
            updatePost += f"**{mod['title']}** has released a new version\n<{changelogUrl}>\n"

            try:
                changelog = await getSteamChangelog(changelogUrl)
            except Exception as e:
                gunicorn_logger.error(f"Error retrieving changelog for {modId}:\n{e}")
                changelog = "Error retrieving changelog"

            updatePost += f"```\n{changelog}```\n"

    steam_timestamp["last_checked"] = now
    with open("steam_timestamp.json", "w") as f:
        json.dump(steam_timestamp, f)

    if updatePost:
        return await utility.sendMessage(settings.STAFF_CHANNEL, f"<@&{settings.ADMIN_ROLE}>\n{updatePost}", ["roles"])
    return None


async def getSteamMods(collection):
    data = {"collectioncount": 1, "publishedfileids[0]": collection}
    mods = []

    r = await utility.post([HTTP_200_OK], f"{STEAM_URL}/GetCollectionDetails/v1/", data=data, headers=None)
    response = r.json()

    for collection in response["response"]["collectiondetails"]:
        for child in collection["children"]:
            if child["filetype"] == 0:
                mods.append(child["publishedfileid"])
            elif child["filetype"] == 2:
                mods += await getSteamMods(child["publishedfileid"])

    return mods


async def getSteamChangelog(changelogUrl):
    r = await utility.get([HTTP_200_OK], changelogUrl, headers=None)
    soup = BeautifulSoup(r.text, features="html.parser")
    headline = soup.find("div", {"class": "changelog headline"})

    return headline.findNext("p").get_text(separator="\n")
