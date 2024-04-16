
import json

import tiktoken
from apify import Actor
from apify_client import ApifyClientAsync
from openai import AsyncOpenAI

from .model import OpenaiAssistantFilesIntegrationInputs
from .utils import split_data_if_required


async def main() -> None:
    async with Actor:

        payload = await Actor.get_input()

        aid = OpenaiAssistantFilesIntegrationInputs(**payload)

        client = AsyncOpenAI(api_key=aid.openai_api_key)
        aclient_apify = ApifyClientAsync()

        if not (assistant := await client.beta.assistants.retrieve(aid.assistant_id)):
            await Actor.fail(status_message=f"Assistant with ID: {aid.assistant_id} was not found at the OpenAI")

        encoding = tiktoken.encoding_for_model(assistant.model)

        resource = payload.get("payload", {}).get("resource", {})
        if not (dataset_id := resource.get("defaultDatasetId") or aid.dataset_id):
            msg = """No Dataset ID provided. It should be provided either in payload or in actor_input."""
            await Actor.fail(status_message=msg)

        dataset = await aclient_apify.dataset(dataset_id).list_items(clean=True, fields=aid.fields)
        data: list = dataset.items
        data = await split_data_if_required(data, encoding)

        # this is not optimal, data are first deleted but then created. It should be vice versa
        # but we are hitting the OpenAI Assistant limits.
        await delete_files(client, aid, assistant)

        # Create assistant files
        for i, d in enumerate(data):
            try:
                filename = (
                    f"{aid.file_prefix}_{aid.dataset_id}_{i}.json" if aid.file_prefix else f"{aid.dataset_id}_{i}.json"
                )
                file = await client.files.create(file=(filename, json.dumps(d).encode("utf-8")), purpose="assistants")
                await client.beta.assistants.files.create(aid.assistant_id, file_id=file.id)
                Actor.log.debug("Created file %s, file_id: %s", file.filename, file.id)
            except Exception as e:
                Actor.log.exception(e)


async def delete_files(client, aid: OpenaiAssistantFilesIntegrationInputs, assistant):

    # only delete files that ara attached to the assistant_id
    files_to_delete = set(aid.file_ids_to_delete) if aid.file_ids_to_delete else set()
    files_to_delete = files_to_delete.intersection(set(assistant.file_ids))

    # delete files with prefix attached to the assistant_id
    files_to_delete = files_to_delete.union(await get_assistant_files_by_prefix(client, aid))

    if files_to_delete:
        Actor.log.debug("Files to delete: %s (also including file_prefix: %s files)", files_to_delete, aid.file_prefix)
        for file_id in files_to_delete:
            try:
                await client.beta.assistants.files.delete(file_id, assistant_id=aid.assistant_id)
                await client.files.delete(file_id)
                Actor.log.debug("Deleted file_id: %s", file_id)
            except Exception as e:
                Actor.log.exception(e)


async def get_assistant_files_by_prefix(client: AsyncOpenAI, aid: OpenaiAssistantFilesIntegrationInputs):
    """ List Assistant files and return file_ids that starts with prefix."""

    files = set()
    if aid.file_prefix:
        for key, f in await client.beta.assistants.files.list(assistant_id=aid.assistant_id):
            if key == "data":
                for assistant_file in f:
                    file_ = await client.files.retrieve(assistant_file.id)
                    if file_.filename.startswith(aid.file_prefix):
                        files.add(assistant_file.id)
    return files