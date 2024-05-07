import time
from unittest.mock import patch

import openai
import pytest
from apify import Actor
from dotenv import load_dotenv

from src.main import (
    create_files_vector_store_and_poll,
    delete_files_from_vector_store, get_files_by_prefix,
    get_vector_store_files_by_ids,
    get_vector_store_files_by_prefix,
)
from tests.conftest import FILE_PREFIX

load_dotenv()

client = openai.AsyncClient()


def print_(*args, **kwargs) -> None:  # type: ignore
    print(args, kwargs)


async def empty(args, **kwargs) -> None:  # type: ignore
    ...


@pytest.mark.asyncio
@pytest.mark.vcr(filter_headers=["Authorization"])
@pytest.mark.integration
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_vector_store_integration(monkeypatch, vector_store_fixture, file_fixture) -> None:  # type: ignore
    """Create a vector store, add files, get vector store files, delete file and vector store"""

    vs = vector_store_fixture

    file_created = file_fixture
    file_prefix = FILE_PREFIX

    monkeypatch.setattr(Actor, "push_data", empty)

    files = await get_files_by_prefix(client, file_prefix)
    assert files
    assert file_created.id in files, "File not found in OpenAI files"

    # attach file to vector store
    vs_batch = await create_files_vector_store_and_poll(client, vs.id, [file_created.id])
    assert vs_batch
    assert vs_batch.file_counts.completed == 1, "File not attached to vector store"

    # get vector store files by id
    files = await get_vector_store_files_by_ids(client, vs.id, [file_created.id])
    assert files
    assert file_created.id in files, "File not found in vector store files"

    # get vector store files by prefix
    files = await get_vector_store_files_by_prefix(client, vs.id, file_prefix)
    assert files
    assert file_created.id in files, "File not found in vector store files"

    # delete files from vector store
    deleted_files = await delete_files_from_vector_store(client, vs.id, [file_created.id])
    assert len(deleted_files) == 1
    assert deleted_files[0].deleted is True, "File not deleted from vector store"

    time.sleep(1)

    files = await get_vector_store_files_by_ids(client, vs.id, [file_created.id])
    assert not files
    assert file_created.id not in files, "File not deleted from vector store"
