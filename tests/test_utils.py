import pytest
import tiktoken

from src.utils import get_nested_value, split_data_if_required, split_data_into_batches

# Mock for Encoding.encode

ENCODING = tiktoken.encoding_for_model("gpt-3.5-turbo")


def test_get_nested_value() -> None:
    data = {"a": "v1", "c1": {"c2": "v2"}}
    assert get_nested_value(data, "a") == "v1"
    assert get_nested_value(data, "c1.c2") == "v2"
    assert get_nested_value(data, "b") == {}


def test_split_data_into_batches() -> None:
    data = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}]
    batches = split_data_into_batches(data, 15, ENCODING)
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


@pytest.mark.asyncio
async def test_split_data_if_required_small_data() -> None:
    data = [{"name": "Alice"}]
    result = await split_data_if_required(data, ENCODING)
    assert result == [data]  # Expecting the data not to be split


@pytest.mark.asyncio
async def test_split_data_if_required_large_data() -> None:

    data = [{"name": "Alice"}] * 1_000_000  # Large dataset
    result = await split_data_if_required(data, ENCODING)
    # Check if data was split into batches as expected
    assert len(result) > 1
