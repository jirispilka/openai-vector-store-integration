import json
from unittest.mock import AsyncMock, patch

import openai
import pytest
from apify import Actor
from apify_client import ApifyClientAsync
from dotenv import load_dotenv
from pydantic import ConfigDict

import src.main
import src.utils
from src.input_model import OpenaiVectorStoreIntegration
from src.main import check_inputs, create_file, create_files_from_dataset, create_files_from_key_value_store, delete_files


class ActorInput(OpenaiVectorStoreIntegration):
    model_config = ConfigDict(str_strip_whitespace = True)

load_dotenv()

client = openai.AsyncClient()
aclient_apify = ApifyClientAsync()


def print_(*args, **kwargs) -> None:  # type: ignore
    print(args, kwargs)


async def empty(args, **kwargs) -> None:  # type: ignore
    ...


async def mock_create_and_poll(*args, **kwargs):  # type: ignore  # noqa: ANN201
    class MockVectorStoreFile:
        def __init__(self) -> None:
            self.status = "completed"
            self.id = "test_file_id"
            self.last_error = ""

    return MockVectorStoreFile()


@pytest.mark.asyncio()
@pytest.mark.integration()
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


@pytest.mark.asyncio()
@pytest.mark.integration()
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_create_files_from_key_value_store(monkeypatch) -> None:  # type: ignore
    # Mock the AsyncOpenAI and ApifyClientAsync objects

    monkeypatch.setattr(Actor, "push_data", empty)

    actor_input = ActorInput(  # type: ignore
        vectorStoreId="xyz",
        openaiApiKey="test_openai_api_key",
        filePrefix="unittest_",
        datasetFields=["text"],
    )

    mock_apify = AsyncMock(spec=ApifyClientAsync)
    mock_apify.key_value_store.return_value.list_keys = AsyncMock(return_value={"items": [{"key": "test_file.pdf"}]})
    mock_apify.key_value_store.return_value.get_record_as_bytes = AsyncMock(
        return_value={"key": "test_file.pdf", "value": b"test_pdf_value"}
    )
    # create mock for VectorStoreFile
    monkeypatch.setattr(client.vector_stores.files, "create_and_poll", mock_create_and_poll)

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


@pytest.mark.asyncio()
async def test_check_inputs_with_assistant_id_logs_warning_and_never_calls_assistants_api(monkeypatch) -> None:  # type: ignore  # noqa: ANN001
    """Regression test for the Assistants API removal.

    Supplying `assistantId` must never trigger a call to `client.beta.assistants.retrieve` (the Assistants
    API is being retired) and must instead produce a logged deprecation warning. Previously, `check_inputs`
    called `client.beta.assistants.retrieve(actor_input.assistantId)` whenever `assistantId` was set.
    """

    actor_input = ActorInput(  # type: ignore
        vectorStoreId="xyz",
        openaiApiKey="test_openai_api_key",
        datasetFields=["text"],
        assistantId="asst_bogus_or_real_it_must_not_matter",
    )

    mock_client = AsyncMock(spec=openai.AsyncOpenAI)
    mock_client.vector_stores.retrieve = AsyncMock(return_value=None)
    # If the Assistants API were ever called, fail loudly rather than silently succeeding.
    mock_client.beta.assistants.retrieve = AsyncMock(side_effect=AssertionError("client.beta.assistants.retrieve must never be called"))

    warnings: list[str] = []
    monkeypatch.setattr(Actor.log, "warning", lambda msg, *args, **kwargs: warnings.append(msg % args if args else msg))  # type: ignore

    payload = {"payload": {"resource": {"defaultDatasetId": "test_dataset_id"}}}
    await check_inputs(mock_client, actor_input, payload)

    mock_client.beta.assistants.retrieve.assert_not_called()
    assert any("assistantId" in w and "deprecated" in w for w in warnings), f"Expected a deprecation warning, got: {warnings}"


@pytest.mark.asyncio()
async def test_check_inputs_without_assistant_id_does_not_log_warning(monkeypatch) -> None:  # type: ignore  # noqa: ANN001
    """Regression test for the falsy arm of the `assistantId` deprecation-warning guard.

    Complements `test_check_inputs_with_assistant_id_logs_warning_and_never_calls_assistants_api`, which only
    exercises `check_inputs` with `assistantId` set. This test covers the default path (no `assistantId`, the
    common case for the majority of users) and confirms no deprecation warning is logged and that the rest of
    `check_inputs` (vector-store retrieval, dataset/key-value-store id resolution) still behaves as before.
    """

    actor_input = ActorInput(  # type: ignore
        vectorStoreId="xyz",
        openaiApiKey="test_openai_api_key",
        datasetFields=["text"],
    )
    assert actor_input.assistantId is None

    mock_client = AsyncMock(spec=openai.AsyncOpenAI)
    mock_client.vector_stores.retrieve = AsyncMock(return_value=None)

    warnings: list[str] = []
    monkeypatch.setattr(Actor.log, "warning", lambda msg, *args, **kwargs: warnings.append(msg % args if args else msg))  # type: ignore

    payload = {"payload": {"resource": {"defaultDatasetId": "test_dataset_id", "defaultKeyValueStoreId": "test_kv_store_id"}}}
    await check_inputs(mock_client, actor_input, payload)

    mock_client.vector_stores.retrieve.assert_awaited_once_with("xyz")
    assert not warnings, f"Expected no deprecation warning when assistantId is not set, got: {warnings}"
    assert actor_input.datasetId == "test_dataset_id"
    assert actor_input.keyValueStoreId == "test_kv_store_id"


@pytest.mark.asyncio()
@pytest.mark.integration()
@pytest.mark.vcr(filter_headers=["Authorization"])
@patch("apify.Actor.log.debug", print_)
@patch("apify.Actor.log.exception", print_)
async def test_create_files_from_dataset(monkeypatch) -> None:  # type: ignore  # noqa: ANN001

    monkeypatch.setattr(Actor, "push_data", empty)

    actor_input = ActorInput(  # type: ignore
        vectorStoreId="xyz",
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

    # create mock for VectorStoreFile
    monkeypatch.setattr(client.vector_stores.files, "create_and_poll", mock_create_and_poll)

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


@pytest.mark.asyncio()
@pytest.mark.integration()
@patch("apify.Actor.log.debug", print_)
async def test_create_files_from_dataset_splits_large_dataset_without_assistant_id(monkeypatch) -> None:  # type: ignore  # noqa: ANN001
    """Regression test for unconditional splitting.

    Before this change, `create_files_from_dataset` only split an oversized dataset when an `Assistant` object was
    available (looked up via the now-removed `assistantId` -> `client.beta.assistants.retrieve` flow); without it,
    the code took the `else: data = [data]` branch and never split, producing a single oversized file that OpenAI
    would reject. Splitting must now happen regardless of `assistantId`.

    `OPENAI_MAX_TOKENS_PER_FILE` also sets the byte pre-check threshold, so monkeypatching it down lets a small
    dataset already exceed both the byte pre-check and the real token limit. This exercises the genuine
    (unmocked) `split_data_if_required` path -- including the real `tiktoken.get_encoding` call -- without
    tokenizing a million items.

    Marked `integration`: still requires the real `o200k_base` tiktoken encoding, which downloads its BPE file
    on a cold cache.
    """

    monkeypatch.setattr(Actor, "push_data", empty)
    monkeypatch.setattr(src.utils, "OPENAI_MAX_TOKENS_PER_FILE", 20)

    actor_input = ActorInput(  # type: ignore
        vectorStoreId="xyz",
        datasetId="test_dataset_id",
        datasetFields=["name"],
        openaiApiKey="test_openai_api_key",
        filePrefix="unittest_",
    )
    assert actor_input.assistantId is None

    class MockDatasetItems:
        def __init__(self, items: list) -> None:
            self.items = items

    # Small dataset -- with OPENAI_MAX_TOKENS_PER_FILE patched down to 20, this is already well over both the
    # byte pre-check threshold and the real token limit, so it exercises the genuine split path cheaply.
    large_data = [{"name": "Alice"}] * 50

    mock_apify = AsyncMock(spec=ApifyClientAsync)
    mock_apify.dataset.return_value.list_items = AsyncMock(return_value=MockDatasetItems(large_data))

    created_batches: list[list] = []

    async def fake_create_file_and_add_to_vector_store(_client, _filename, data, _vector_store_id):  # type: ignore  # noqa: ANN001
        # `data` is the JSON-serialized bytes of one batch (see create_files_from_dataset's call site);
        # decode it back so the assertion below can check the actual split content, not just its encoding.
        created_batches.append(json.loads(data.decode("utf-8")))

        class MockFile:
            id = f"file_{len(created_batches)}"

        return MockFile()

    monkeypatch.setattr(src.main, "create_file_and_add_to_vector_store", fake_create_file_and_add_to_vector_store)

    files_created = await create_files_from_dataset(client, mock_apify, actor_input)

    assert len(files_created) > 1, "Expected the oversized dataset to be split into multiple files even without assistantId"
    assert len(created_batches) == len(files_created)
    # Content round-trips: every input item ends up in exactly one output batch, in the original order --
    # a real assertion about the split output, not just a count that trivially matches the fake's bookkeeping.
    assert [item for batch in created_batches for item in batch] == large_data
