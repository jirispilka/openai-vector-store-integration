from __future__ import annotations

import json
from typing import TYPE_CHECKING

import tiktoken
from apify import Actor
from apify_client import ApifyClientAsync
from openai import AsyncOpenAI

from .input_model import OpenaiAssistantFilesIntegrationInputs
from .utils import get_nested_value, split_data_if_required

if TYPE_CHECKING:
    from openai.types.beta import Assistant
    from openai.types.file_object import FileObject


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
        if not (dataset_id := resource.get("defaultDatasetId") or aid.dataset_id or ""):
            msg = """No Dataset ID provided. It should be provided either in payload or in actor_input."""
            await Actor.fail(status_message=msg)

        dataset = await aclient_apify.dataset(dataset_id).list_items(clean=True)
        data: list = dataset.items

        if aid.fields:
            Actor.log.debug("Selecting the following fields %s", aid.fields)
            data = [{key: get_nested_value(d, key) for key in aid.fields} for d in data]
            data = [d for d in data if d]

        data = await split_data_if_required(data, encoding)
        file_ids_to_delete = await get_file_ids_to_delete(client, aid, assistant)

        # 1 - Create files
        store = await Actor.open_key_value_store()

        files_created = []
        try:
            for i, d in enumerate(data):
                prefix = f"{aid.file_prefix}_{aid.dataset_id}" if aid.file_prefix else f"{aid.dataset_id}"
                filename = f"{prefix}_{i}.json"
                file = await client.files.create(file=(filename, json.dumps(d).encode("utf-8")), purpose="assistants")
                Actor.log.debug("Created file %s, file_id: %s", file.filename, file.id)
                await store.set_value(filename, json.dumps(d), content_type="application/json")
                Actor.log.debug("Stored the file in Actor's key value store file: %s", file.filename)
                files_created.append(file)
        except Exception as e:
            Actor.log.exception(e)

        # 2 - detach existing files from the assistant
        await detach_assistant_files(client, aid.assistant_id, file_ids_to_delete)

        # 3 - attach new files
        await attach_assistant_files(client, aid.assistant_id, files_created)

        # delete files
        await delete_files(client, file_ids_to_delete)


async def attach_assistant_files(client: AsyncOpenAI, assistant_id: str, files_created: list[FileObject]) -> None:
    try:
        for file in files_created:
            await client.beta.assistants.files.create(assistant_id, file_id=file.id)
            Actor.log.debug("Attached file %s, file_id: %s to the assistant", file.filename, file.id)
    except Exception as e:
        Actor.log.exception(e)


async def get_file_ids_to_delete(
    client: AsyncOpenAI, aid: OpenaiAssistantFilesIntegrationInputs, assistant: Assistant
) -> set:
    """Only delete files that are associated with the assistant_id."""

    files_to_delete = set(aid.file_ids_to_delete) if aid.file_ids_to_delete else set()
    files_to_delete = files_to_delete.intersection(set(assistant.file_ids))

    # get files with prefix associated with the assistant_id
    return files_to_delete.union(await get_assistant_files_by_prefix(client, aid))


async def detach_assistant_files(client: AsyncOpenAI, assistant_id: str, files_to_delete: set) -> None:
    """Detach files from the assistant.

    Note that file is not actually deleted. Only the association is removed.

    https://platform.openai.com/docs/api-reference/assistants/deleteAssistantFile
    """

    try:
        for file_id in files_to_delete:
            await client.beta.assistants.files.delete(file_id, assistant_id=assistant_id)
            Actor.log.debug("Detached file_id: %s", file_id)
    except Exception as e:
        Actor.log.exception(e)


async def delete_files(client: AsyncOpenAI, files_to_delete: set) -> None:
    """
    Delete OpenAI files.

    https://platform.openai.com/docs/api-reference/files/delete
    """

    Actor.log.debug("Files to delete: %s", files_to_delete)
    try:
        for file_id in files_to_delete:
            await client.files.delete(file_id)
            Actor.log.debug("Deleted file_id: %s", file_id)
    except Exception as e:
        Actor.log.exception(e)


async def get_assistant_files_by_prefix(client: AsyncOpenAI, aid: OpenaiAssistantFilesIntegrationInputs) -> set:
    """List Assistant files and return file_ids that starts with prefix.

    https://platform.openai.com/docs/api-reference/assistants/listAssistantFiles
    """

    if not aid.file_prefix:
        return set()

    files = set()
    for key, f in await client.beta.assistants.files.list(assistant_id=aid.assistant_id):
        if key == "data":
            try:
                for assistant_file in f:
                    file_ = await client.files.retrieve(assistant_file.id)
                    if file_.filename.startswith(aid.file_prefix):
                        files.add(assistant_file.id)
            except Exception as e:
                Actor.log.warning(e)
    return files
