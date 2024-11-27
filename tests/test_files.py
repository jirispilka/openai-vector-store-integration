from unittest.mock import AsyncMock, patch

import openai
import pytest
from apify import Actor
from apify_client import ApifyClientAsync
from dotenv import load_dotenv

from src.input_model import OpenaiVectorStoreIntegration as ActorInput
from src.main import create_file, create_files_from_dataset, create_files_from_key_value_store, delete_files

load_dotenv()

client = openai.AsyncClient()
aclient_apify = ApifyClientAsync()


def print_(*args, **kwargs) -> None:  # type: ignore
    print(args, kwargs)


async def empty(args, **kwargs) -> None:  # type: ignore
    ...


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_openai_files_integration(monkeypatch) -> None:  # type: ignore
    """Create a file, list files, retrieve file, read file, delete file."""

    monkeypatch.setattr(Actor, "push_data", empty)

    filename = "unittest_file.txt"
    filedata = b"Hello, OpenAI!"

    file = await create_file(client, filename, filedata)
    assert file is not None

    file_r = await client.files.retrieve(file.id)
    assert file_r is not None
    assert file_r.status == "processed"

    file_d = await delete_files(client, [str(file.id)])
    assert file_d
    assert file_d[0].deleted is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_create_files_from_key_value_store(monkeypatch, vector_store_fixture) -> None:  # type: ignore
    # Mock the AsyncOpenAI and ApifyClientAsync objects

    monkeypatch.setattr(Actor, "push_data", empty)

    actor_input = ActorInput(  # type: ignore
        vectorStoreId=vector_store_fixture.id,
        openaiApiKey="test_openai_api_key",
        filePrefix="unittest_",
        datasetFields=["text"],
    )

    mock_apify = AsyncMock(spec=ApifyClientAsync)
    mock_apify.key_value_store.return_value.list_keys = AsyncMock(return_value={"items": [{"key": "test_file.pdf"}]})
    mock_apify.key_value_store.return_value.get_record_as_bytes = AsyncMock(
        return_value={"key": "test_file.pdf", "value": b"test_pdf_value"}
    )

    # Call the function with the mock objects
    files_created = await create_files_from_key_value_store(client, mock_apify, actor_input)
    assert files_created

    file = files_created[0]
    assert file.filename.startswith(str(actor_input.filePrefix)), "File prefix does not match"

    # Check that file was created
    file_r = await client.files.retrieve(file.id)
    assert file_r is not None
    assert file_r.status == "processed", "File was not created successfully"

    # Clean up
    file_d = await delete_files(client, [str(file.id)])
    assert file_d
    assert file_d[0].deleted is True


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_create_files_from_dataset(monkeypatch, vector_store_fixture) -> None:  # type: ignore  # noqa: ANN001

    monkeypatch.setattr(Actor, "push_data", empty)

    actor_input = ActorInput(  # type: ignore
        vectorStoreId=vector_store_fixture.id,
        datasetId="test_dataset_id",
        datasetFields=["text"],
        openaiApiKey="test_openai_api_key",
        filePrefix="unittest_",
    )

    class MockDatasetItems:
        def __init__(self, items: list) -> None:
            self.items = items

    # In your test function

    mock_apify = AsyncMock(spec=ApifyClientAsync)
    mock_apify.dataset.return_value.list_items = AsyncMock(return_value=MockDatasetItems([{"text": "test_text"}]))

    # Call the function with the mock objects
    files_created = await create_files_from_dataset(client, mock_apify, actor_input)
    assert files_created

    file = files_created[0]
    assert file.filename.startswith(str(actor_input.filePrefix)), "File prefix does not match"

    # Check that file was created
    file_r = await client.files.retrieve(file.id)
    assert file_r is not None
    assert file_r.status == "processed", "File was not created successfully"

    # Clean up
    file_d = await delete_files(client, [str(file.id)])
    assert file_d
    assert file_d[0].deleted is True
