from __future__ import annotations

import json
from io import BytesIO
from typing import TYPE_CHECKING, Generator

import openai
import tiktoken
from apify import Actor
from apify_client import ApifyClientAsync
from openai import AsyncOpenAI

from .constants import OPENAI_FILE_BATCHES_MAX_SIZE, OPENAI_SUPPORTED_FILES
from .input_model import OpenaiVectorStoreIntegration as ActorInput
from .utils import get_nested_value, split_data_if_required

if TYPE_CHECKING:
    from openai.types import FileDeleted
    from openai.types.beta import Assistant
    from openai.types.beta.vector_stores import VectorStoreFileBatch, VectorStoreFileDeleted
    from openai.types.file_object import FileObject


async def main() -> None:
    async with Actor:
        payload = await Actor.get_input()
        actor_input = ActorInput(**payload)

        client = AsyncOpenAI(api_key=actor_input.openaiApiKey)
        aclient_apify = ApifyClientAsync()

        Actor.log.info("Starting OpenAI Vector Store Integration, checking inputs ...")
        assistant = await check_inputs(client, actor_input, payload)

        Actor.log.info("Get existing files in the vector store")
        file_ids_to_delete = await get_vector_store_file_ids(client, actor_input.vectorStoreId, actor_input.fileIdsToDelete, actor_input.filePrefix)

        # 1 - create files from dataset or from key-value store
        files_created: list[str] = []
        if actor_input.datasetId:
            Actor.log.info("Creating files from Apify's dataset")
            files: list[FileObject] = await create_files_from_dataset(client, aclient_apify, actor_input, assistant)
            files_created.extend(f.id for f in files)

        if actor_input.saveCrawledFiles and actor_input.keyValueStoreId:
            Actor.log.info("Creating files from Apify's key-value store")
            files = await create_files_from_key_value_store(client, aclient_apify, actor_input)
            files_created.extend(f.id for f in files)

        # 2 - remove files from vector store
        if file_ids_to_delete:
            await delete_files_from_vector_store(client, actor_input.vectorStoreId, file_ids_to_delete)

        #  3 - add to vector store in batch and poll for results
        if files_created:

            def _batch(iterable: list, n: int = OPENAI_FILE_BATCHES_MAX_SIZE) -> Generator:
                for ndx in range(0, len(iterable), n):
                    yield iterable[ndx : min(ndx + n, len(iterable))]

            for batch_files in _batch(files_created):
                await create_files_vector_store_and_poll(client, actor_input.vectorStoreId, batch_files)

        # 4 - delete all files
        if file_ids_to_delete:
            await delete_files(client, file_ids_to_delete)


async def check_inputs(client: AsyncOpenAI, actor_input: ActorInput, payload: dict) -> Assistant | None:
    """Check that provided input exists at OpenAI or at Apify."""

    try:
        await client.beta.vector_stores.retrieve(actor_input.vectorStoreId)
    except openai.NotFoundError:
        msg = (
            f"Unable to find the OpenAI Vector Store with the ID: {actor_input.vectorStoreId}. Please verify that the Vector Store has "
            "been correctly created and that the `vectorStoreId` provided is accurate."
        )
        Actor.log.error(msg)
        await Actor.fail(status_message=msg)
    except openai.AuthenticationError:
        msg = "The OpenAI API Key provided is invalid. Please verify that the `OPENAI_API_KEY` is correctly set."
        Actor.log.error(msg)
        await Actor.fail(status_message=msg)

    assistant = None
    if actor_input.assistantId and not (assistant := await client.beta.assistants.retrieve(actor_input.assistantId)):
        msg = f"Unable to find the Assistant with the ID: {actor_input.assistantId} on OpenAI. "
        "Please verify that the Assistant has been correctly created and that the `assistantId` provided is accurate. "
        Actor.log.error(msg)
        await Actor.fail(status_message=msg)

    resource = payload.get("payload", {}).get("resource", {})
    dataset_id = resource.get("defaultDatasetId") or actor_input.datasetId or ""
    key_value_store_id = resource.get("defaultKeyValueStoreId") or actor_input.keyValueStoreId or ""

    if not (dataset_id or key_value_store_id):
        msg = (
            "The Apify's `datasetId` or Apify's `keyValueStoreId` are not provided. "
            "There are two ways to specify the `datasetId` or `keyValueStoreId`: "
            "1. Automatic Input: If this integration is used with other Actors, such as the Website Content Crawler, the variables should be "
            "automatically passed in the 'payload'. Please check the `Input` payload to ensure that they are included."
            "2. Manual Input: If you are running this Actor independently, you can to manually specify the 'datasetId' or `keyValueStoreId. "
            "You can do this by entering the values in the 'Debug Settings' section of the Actor's input screen."
            "Please verify that one of these options is correctly configured."
        )
        Actor.log.error(msg)
        await Actor.fail(status_message=msg)

    actor_input.datasetId = dataset_id
    actor_input.keyValueStoreId = key_value_store_id
    return assistant


async def create_files_from_dataset(
    client: AsyncOpenAI, aclient_apify: ApifyClientAsync, actor_input: ActorInput, assistant: Assistant | None = None
) -> list[FileObject]:
    """Create files in OpenAI."""

    dataset = await aclient_apify.dataset(str(actor_input.datasetId)).list_items(clean=True)
    data: list = dataset.items

    if actor_input.datasetFields:
        Actor.log.info("Selecting the following fields %s", actor_input.datasetFields)
        data = [{key: get_nested_value(d, key) for key in actor_input.datasetFields} for d in data]
        data = [d for d in data if d]

    if encoding := assistant and tiktoken.encoding_for_model(assistant.model) or None:
        data = await split_data_if_required(data, encoding)
    else:
        data = [data]

    files_created = []
    try:
        for i, d in enumerate(data):
            prefix = f"{actor_input.filePrefix}_{actor_input.datasetId}" if actor_input.filePrefix else f"{actor_input.datasetId}"
            filename = f"{prefix}_{i}.json"
            if f := await create_file(client, filename, json.dumps(d).encode("utf-8")):
                files_created.append(f)
    except Exception as e:
        Actor.log.exception(e)

    # store files in Apify's KV store if enabled
    if actor_input.saveInApifyKeyValueStore:
        await save_in_apify_kv_store(files_created, data)

    return files_created


async def create_files_from_key_value_store(client: AsyncOpenAI, aclient_apify: ApifyClientAsync, actor_input: ActorInput) -> list[FileObject]:
    """Create files from Apify key-value store."""

    files_created = []
    exclusive_start_key = None
    kv_store = aclient_apify.key_value_store(str(actor_input.keyValueStoreId))

    while keys := await kv_store.list_keys(exclusive_start_key=exclusive_start_key):
        Actor.log.info("Creating files from Apify key-value store, key value store items: %s", len(keys.get("items", [])))

        for item in keys.get("items", []):
            key = item.get("key")
            ext = f".{key.split('.')[-1]}"
            prefix = f"{actor_input.filePrefix}_{actor_input.keyValueStoreId}" if actor_input.filePrefix else f"{actor_input.keyValueStoreId}"

            if ext in OPENAI_SUPPORTED_FILES:
                if d := await kv_store.get_record_as_bytes(key):
                    filename = f"{prefix}_{d['key']}"
                    if f := await create_file(client, filename, BytesIO(d["value"])):
                        files_created.append(f)
            else:
                Actor.log.debug("Skipping file %s not supported by OpenAI", item.get("key"))

        if not (exclusive_start_key := keys.get("nextExclusiveStartKey", None)):
            return files_created

    return files_created


async def create_file(client: AsyncOpenAI, filename: str, data: bytes | BytesIO) -> FileObject | None:
    """Create OpenAI file and push information to Apify's output.

    https://platform.openai.com/docs/api-reference/files/create
    """

    try:
        file = await client.files.create(file=(filename, data), purpose="assistants")
        Actor.log.info("Created OpenAI file: %s, id: %s", file.filename, file.id)
        await Actor.push_data({"filename": filename, "file_id": file.id, "status": "created"})
        return file  # noqa: TRY300
    except Exception as e:
        Actor.log.error("Failed to create OpenAI file: %s, error: %s", filename, e)

    return None


async def delete_files(client: AsyncOpenAI, files_to_delete: list[str]) -> list[FileDeleted]:
    """
    Delete OpenAI files.

    https://platform.openai.com/docs/api-reference/files/delete
    """
    deleted_files = []
    files_to_delete = files_to_delete or []
    Actor.log.info("About to delete files from OpenAI. Number of files: %s", len(files_to_delete))

    try:
        for _id in files_to_delete:
            file_ = await client.files.delete(_id)
            Actor.log.info("Deleted OpenAI File with id: %s", _id)
            await Actor.push_data({"filename": "", "file_id": file_.id, "status": "deleted"})
            deleted_files.append(file_)
    except Exception as e:
        Actor.log.exception(e)

    return deleted_files


async def create_files_vector_store_and_poll(client: AsyncOpenAI, vs_id: str, files_created: list[str]) -> VectorStoreFileBatch | None:
    """Create files in vector store and poll for the results. There is a limit of 500 files per batch."""
    try:
        v = await client.beta.vector_stores.file_batches.create_and_poll(vector_store_id=vs_id, file_ids=files_created)
        Actor.log.info("Created files in vector store: %s", v)
        return v  # noqa: TRY300
    except Exception as e:
        Actor.log.exception(e)

    return None


async def delete_files_from_vector_store(client: AsyncOpenAI, vs_id: str, file_ids: list[str]) -> list[VectorStoreFileDeleted]:
    """Remove files from vector store. The files are not actually deleted, only removed."""

    deleted_files = []
    file_ids = file_ids or []
    Actor.log.info("About to delete files from vector store. Number of files: %s", len(file_ids))

    try:
        for _id in file_ids:
            file_ = await client.beta.vector_stores.files.delete(_id, vector_store_id=vs_id)
            Actor.log.info("Removed file from vector store: %s", file_)
            deleted_files.append(file_)
    except Exception as e:
        Actor.log.exception(e)

    return deleted_files


async def get_files_by_prefix(client: AsyncOpenAI, file_prefix: str) -> list[str]:
    """Get files with a specific prefix from OpenAI's file store."""

    files = [f async for f in client.files.list()]
    return [f.id for f in files if f.filename.startswith(file_prefix)]


async def get_vector_store_files_by_ids(client: AsyncOpenAI, vs_id: str, file_ids: list[str]) -> list[str]:
    """Find files in vector store by file ids."""

    vs_files = [f async for f in client.beta.vector_stores.files.list(vector_store_id=vs_id)]
    files = [f.id for f in vs_files if f.id in file_ids]

    if set(file_ids) - set(files):
        Actor.log.warning(
            "The following file ids were provided in the input but were not found in the vector store: %s, "
            "If you want to really delete them, you will have to do it manually.",
            set(file_ids) - set(files),
        )

    return files


async def get_vector_store_files_by_prefix(client: AsyncOpenAI, vs_id: str, file_prefix: str) -> list[str]:
    """Find files in vector store by file prefix.

    Get files with prefix from OpenAI's file store, then retrieve the files associated with the vector store and compare them.
    """

    files = await get_files_by_prefix(client, file_prefix)
    vs_files = [f async for f in client.beta.vector_stores.files.list(vector_store_id=vs_id)]

    file_present = [f.id for f in vs_files if f.id in files]
    for f in (f.id for f in vs_files if f.id not in files):
        Actor.log.warning(
            f"File {f} associated with vector store: {vs_id} was not found in the OpenAI Files. This "
            "typically means that the file was deleted but is still associated with vector store."
            "You need to solve this issue manually if desired.",
        )

    return file_present


async def get_vector_store_file_ids(client: AsyncOpenAI, vs_id: str, file_ids: list | None, file_prefix: str | None) -> list[str]:
    """Find files in vector store, either using file_ids and/or by file prefix."""

    file_ids = file_ids or []
    file_prefix = file_prefix or ""

    if not file_ids and not file_prefix:
        return []

    files = []
    if file_ids:
        files.extend(await get_vector_store_files_by_ids(client, vs_id, file_ids))

    if file_prefix:
        files.extend(await get_vector_store_files_by_prefix(client, vs_id, file_prefix))

    return files


async def save_in_apify_kv_store(files_created: list[FileObject], data: list[dict]) -> None:
    """Save files in Apify's KV Store for the debugging purposes."""

    if len(files_created) != len(data):
        Actor.log.warning("Number of files created does not match the number of data. Saving to Apify's KV store skipped")
        return

    try:
        store = await Actor.open_key_value_store()
        for file, d in zip(files_created, data):
            await store.set_value(file.filename, json.dumps(d), content_type="application/json")
            Actor.log.debug("Stored the file in the Actor's key value store: %s", file.filename)
    except Exception as e:
        Actor.log.exception(e)
