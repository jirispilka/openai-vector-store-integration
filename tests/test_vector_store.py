import asyncio
from unittest.mock import patch

import openai
import pytest
from apify import Actor
from dotenv import load_dotenv

from src.main import (
    create_files_vector_store_and_poll,
    delete_files_from_vector_store,
    get_files_by_prefix,
    get_vector_store_files_by_ids,
    get_vector_store_files_by_prefix,
)

load_dotenv()

client = openai.AsyncClient()


def print_(*args, **kwargs) -> None:  # type: ignore  # noqa: ANN002, ANN003
    print(args, kwargs)


async def empty(args, **kwargs) -> None:  # type: ignore  # noqa: ANN003, ARG001, ANN001
    ...


@pytest.mark.asyncio()
@pytest.mark.integration()
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_vector_store_get_by_prefix(monkeypatch, vector_store_fixture, file_fixture) -> None:  # type: ignore  # noqa: ANN001
    """Vector store and file is created using fixture. Check that file with the prefix exists"""

    vs = vector_store_fixture
    file_created = file_fixture
    file_prefix = file_fixture.filename.split("__")[0]

    monkeypatch.setattr(Actor, "push_data", empty)

    files = await get_files_by_prefix(client, file_prefix)
    assert files
    assert file_created.id in files, "File not found in OpenAI files"

    # attach file to vector store
    vs_batch = await create_files_vector_store_and_poll(client, vs.id, [file_created.id])
    assert vs_batch
    assert vs_batch.file_counts.completed == 1, "File not attached to vector store"

    # get vector store files by prefix
    files = await get_vector_store_files_by_prefix(client, vs.id, file_prefix)
    assert files
    assert file_created.id in files, "File not found in vector store files"


@pytest.mark.asyncio()
@pytest.mark.integration()
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_vector_store_get_by_id(monkeypatch, vector_store_fixture, file_fixture) -> None:  # type: ignore  # noqa: ANN001
    """Vector store and file is created using fixture. Check that file with the ID exists"""

    vs = vector_store_fixture
    file_created = file_fixture

    monkeypatch.setattr(Actor, "push_data", empty)

    files = await get_vector_store_files_by_ids(client, vs.id, [file_created.id])
    assert not files
    assert file_created.id not in files, "File not found in vector store files"

    # attach file to vector store
    vs_batch = await create_files_vector_store_and_poll(client, vs.id, [file_created.id])
    assert vs_batch
    assert vs_batch.file_counts.completed == 1, "File not attached to vector store"

    # get vector store files by id
    files = await get_vector_store_files_by_ids(client, vs.id, [file_created.id])
    assert files
    assert file_created.id in files, "File not found in vector store files"


@pytest.mark.asyncio()
@pytest.mark.integration()
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_vector_store_delete(monkeypatch, vector_store_fixture, file_fixture) -> None:  # type: ignore  # noqa: ANN001, ARG001
    """Vector store and file is created using fixture. Check that file is deleted from vector store"""

    vs = vector_store_fixture
    file_created = file_fixture

    vs_batch = await create_files_vector_store_and_poll(client, vs.id, [file_created.id])
    assert vs_batch, "File not attached to vector store"
    assert vs_batch.file_counts.completed == 1, "File not attached to vector store"

    # delete files from vector store
    deleted_files = await delete_files_from_vector_store(client, vs.id, [file_created.id])
    assert len(deleted_files) == 1, "File not deleted from vector store"
    assert deleted_files[0].deleted is True, "File not deleted from vector store"

    await asyncio.sleep(3)

    # the file was deleted - it should not be in the vector store
    files = await get_vector_store_files_by_ids(client, vs.id, [file_created.id])
    assert not files
    assert file_created.id not in files, "File not deleted from vector store"
