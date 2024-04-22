from __future__ import annotations

import json
from typing import TYPE_CHECKING

import tiktoken
from apify import Actor
from apify_client import ApifyClientAsync
from openai import AsyncOpenAI, NotFoundError

from .input_model import OpenaiVectorStoreIntegration as Inputs
from .utils import get_nested_value, split_data_if_required

if TYPE_CHECKING:
    from openai.types.beta import Assistant
    from openai.types.file_object import FileObject


async def main() -> None:
    async with Actor:

        payload = await Actor.get_input()
        aid = Inputs(**payload)

        client = AsyncOpenAI(api_key=aid.openai_api_key)
        aclient_apify = ApifyClientAsync()

        assistant, dataset_id = await check_inputs(client, aid, payload)

        dataset = await aclient_apify.dataset(dataset_id).list_items(clean=True)
        data: list = dataset.items

        if aid.fields:
            Actor.log.debug("Selecting the following fields %s", aid.fields)
            data = [{key: get_nested_value(d, key) for key in aid.fields} for d in data]
            data = [d for d in data if d]

        if encoding := assistant and tiktoken.encoding_for_model(assistant.model) or None:
            data = await split_data_if_required(data, encoding)
        else:
            data = [data]

        file_ids_to_delete = await get_file_ids_to_delete(
            client, aid.file_ids_to_delete, aid.file_prefix, aid.vector_store_id
        )

        # 1 - Create files (also store in Apify's KV store if enabled)
        files_created = await create_files(client, data, aid.dataset_id, aid.file_prefix)
        if aid.save_in_apify_key_value_store:
            await save_in_apify_kv_store(files_created, data)

        # 2 - remove files from vector store
        await delete_files_from_vector_store(client, aid.vector_store_id, file_ids_to_delete)

        #  3 - add to vector store in batch and poll for results
        await create_files_vector_store_and_poll(client, aid.vector_store_id, files_created)

        # 4 - delete all files
        await delete_files(client, file_ids_to_delete)


async def check_inputs(client: AsyncOpenAI, aid: Inputs, payload: dict) -> tuple[Assistant | None, str]:
    """Check that provided input exists at OpenAI or at Apify."""

    if not (await client.beta.vector_stores.retrieve(aid.vector_store_id)):
        await Actor.fail(status_message=f"Vector Store with ID: {aid.vector_store_id} was not found at the OpenAI")

    assistant = None
    if aid.assistant_id and not (assistant := await client.beta.assistants.retrieve(aid.assistant_id)):
        await Actor.fail(status_message=f"Assistant with ID: {aid.assistant_id} was not found at the OpenAI")

    resource = payload.get("payload", {}).get("resource", {})
    if not (dataset_id := resource.get("defaultDatasetId") or aid.dataset_id or ""):
        msg = """No Dataset ID provided. It should be provided either in payload or in actor_input."""
        await Actor.fail(status_message=msg)

    aid.dataset_id = dataset_id
    return assistant, dataset_id


async def create_files(
    client: AsyncOpenAI, data: list[dict], dataset_id: str | None, file_prefix: str | None
) -> list[FileObject]:
    """Create files in OpenAI."""

    files_created = []
    try:
        for i, d in enumerate(data):
            prefix = f"{file_prefix}_{dataset_id}" if file_prefix else f"{dataset_id}"
            filename = f"{prefix}_{i}.json"
            file = await client.files.create(file=(filename, json.dumps(d).encode("utf-8")), purpose="assistants")
            Actor.log.debug("Created OpenAI file: %s, id: %s", file.filename, file.id)
            await Actor.push_data({"filename": filename, "file_id": file.id, "status": "created"})
            files_created.append(file)
    except Exception as e:
        Actor.log.exception(e)

    return files_created


async def create_files_vector_store_and_poll(client: AsyncOpenAI, vs_id: str, files_created: list) -> None:
    try:
        v = await client.beta.vector_stores.file_batches.create_and_poll(
            vector_store_id=vs_id, file_ids=[f.id for f in files_created]
        )
        Actor.log.debug("Created files in vector store: %s", v)
    except Exception as e:
        Actor.log.exception(e)


async def delete_files(client: AsyncOpenAI, files_to_delete: list[str]) -> None:
    """
    Delete OpenAI files.

    https://platform.openai.com/docs/api-reference/files/delete
    """
    files_to_delete = files_to_delete or []

    Actor.log.debug("Files ids to delete: %s", files_to_delete)
    try:
        for _id in files_to_delete:
            file_ = await client.files.delete(_id)
            Actor.log.debug("Deleted OpenAI File with id: %s", _id)
            await Actor.push_data({"filename": "", "file_id": file_.id, "status": "deleted"})
    except Exception as e:
        Actor.log.exception(e)


async def delete_files_from_vector_store(client: AsyncOpenAI, vs_id: str, file_ids_to_delete: list[str]) -> None:
    """Remove files from vector store. The files are not actually deleted, only removed."""

    file_ids_to_delete = file_ids_to_delete or []
    try:
        for _id in file_ids_to_delete:
            file_ = await client.beta.vector_stores.files.delete(_id, vector_store_id=vs_id)
            Actor.log.debug("Removed file from vector store: %s", file_)
    except Exception as e:
        Actor.log.exception(e)


async def get_file_ids_to_delete(
    client: AsyncOpenAI, file_ids: list | None, file_prefix: str | None, vs_id: str
) -> list[str]:
    """Find files to be deleted using file_ids and/or by file prefix.

    Only delete files that are associated with the vector store.
    """

    file_ids = file_ids or []
    file_prefix = file_prefix or ""

    if not file_ids and not file_prefix:
        return []

    vs_files = await client.beta.vector_stores.files.list(vector_store_id=vs_id)
    Actor.log.debug("Files associated with the vector store: %s", [f.id for f in vs_files.data])

    files_to_delete = []
    for f in vs_files.data:
        if f.id in file_ids:
            files_to_delete.append(f.id)
        elif file_prefix:
            try:
                file_ = await client.files.retrieve(f.id)
                if file_.filename.startswith(file_prefix):
                    files_to_delete.append(f.id)
            except NotFoundError:
                Actor.log.warning(
                    "File %s associated with vector store: %s was not found in the OpenAI Files. This "
                    "typically means that the file was deleted but is still associated with vector store."
                    "You need to solve this issue manually if desired.",
                    f.id,
                    vs_id,
                )

    if set(file_ids) - set(files_to_delete):
        Actor.log.warning(
            "The following file ids were provided in the input but not found in the vector store: %s, If you want to "
            "really delete them, you will have to do it manually.",
            set(file_ids) - set(files_to_delete),
        )

    return files_to_delete


async def save_in_apify_kv_store(files_created: list[FileObject], data: list[dict]) -> None:
    """Save files in Apify's KV Store for the debugging purposes."""

    if len(files_created) != len(data):
        Actor.log.warning(
            "Number of files created does not match the number of data. Saving to Apify's KV store skipped"
        )
        return

    try:
        store = await Actor.open_key_value_store()
        for file, d in zip(files_created, data):
            await store.set_value(file.filename, json.dumps(d), content_type="application/json")
            Actor.log.debug("Stored the file in the Actor's key value store: %s", file.filename)
    except Exception as e:
        Actor.log.exception(e)
