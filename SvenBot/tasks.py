import json
import logging

from starlette.status import HTTP_200_OK

from SvenBot import utility

gunicorn_logger = logging.getLogger('gunicorn.error')


async def a3sync_task():
    r = await utility.get([HTTP_200_OK], f'{utility.REPO_URL}/repo')
    repoInfo = r.json()

    with open('revision.json', 'r') as f:
        revision = json.load(f)

    if repoInfo['revision'] != revision['revision']:
        r = await utility.get([HTTP_200_OK], f'{utility.REPO_URL}/changelog')
        changelogs = r.json()['list']

        newRepoSize = round((float(repoInfo["totalFilesSize"]) / 1000000000), 2)
        updatePost = f"```md\n# The A3Sync repo has changed #\n\n[{newRepoSize} GB]\n```\n"
        for changelog in changelogs:
            if changelog['revision'] > revision['revision']:
                new = '' if (len(changelog["newAddons"]) == 0) else "< New >\n{}".format(
                    "\n".join(changelog["newAddons"]))
                deleted = '' if (len(changelog["deletedAddons"]) == 0) else "\n\n< Deleted >\n{}".format(
                    "\n".join(changelog["deletedAddons"]))
                updated = '' if (len(changelog["updatedAddons"]) == 0) else "\n\n< Updated >\n{}".format(
                    "\n".join(changelog["updatedAddons"]))
                if len(new + deleted + updated) > 0:
                    updatePost += f"```md\n{new}{deleted}{updated}\n```\n"

        revision['revision'] = changelog['revision']

        with open('revision.json', 'w') as f:
            json.dump(revision, f)

        return await utility.sendMessage(utility.ANNOUNCE_CHANNEL, updatePost)
    return None


async def recruit_task():
    gunicorn_logger.info(f"Recruit task")
    return await utility.sendMessage(utility.STAFF_CHANNEL,
                                     f"<@&{utility.ADMIN_ROLE}> Post recruitment on <https://www.reddit.com/r/FindAUnit>",
                                     ["roles"])
