import pytest
import tiktoken

from src.utils import get_nested_value, split_data_if_required, split_data_into_batches

# Mock for Encoding.encode

ENCODING = tiktoken.encoding_for_model("gpt-4-mini")


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


def test_list_index_access() -> None:
    data = {"cards": [{"name": "card1"}, {"name": "card2"}]}
    assert get_nested_value(data, "cards[0].name") == "card1"
    assert get_nested_value(data, "cards[1].name") == "card2"
    assert not get_nested_value(data, "cards[2].name")
    assert not get_nested_value(data, "cards[0].invalid_key")


def test_list_slicing() -> None:
    data = {"cards": [{"name": "card1"}, {"name": "card2"}]}
    assert get_nested_value(data, "cards[:].name") == "card1 card2"
    data_empty = {"cards": []}
    assert not get_nested_value(data_empty, "cards[:].name")
    assert not get_nested_value(data, "cards[:].invalid_key")

def test_edge_cases() -> None:
    data = {}
    assert not get_nested_value(data, "a.b.c")
    data = {"a": None}
    assert not get_nested_value(data, "a.b.c")
    assert not get_nested_value({}, "a.b.c")

def test_mixed_list_and_dict() -> None:
    data = {"a": [{"b": {"c": "value1"}}, {"b": {"c": "value2"}}]}
    assert get_nested_value(data, "a[:].b.c") == "value1 value2"
    assert get_nested_value(data, "a[0].b.c") == "value1"
    assert get_nested_value(data, "a[1].b.c") == "value2"
    assert not get_nested_value(data, "a[2].b.c")
    assert not get_nested_value(data, "a[:].b.invalid_key")

def test_complex_nested_structure() -> None:
    data = {
        "users": [
            {"name": "user1", "address": {"city": "City1"}},
            {"name": "user2", "address": {"city": "City2"}}
        ],
        "settings": {"theme": "dark"}
    }
    assert get_nested_value(data, "users[0].name") == "user1"
    assert get_nested_value(data, "users[:].name") == "user1 user2"
    assert get_nested_value(data, "users[:].address.city") == "City1 City2"
    assert get_nested_value(data, "settings.theme") == "dark"
    assert not get_nested_value(data, "settings.invalid_key")

def test_invalid_keys() -> None:
    data = {"cards": [{"name": "card1"}, {"name": "card2"}]}
    assert not get_nested_value(data, "cards[].name")
    assert not get_nested_value(data, "cards[invalid].name")
    assert not get_nested_value(data, "")


@pytest.mark.asyncio()
async def test_split_data_if_required_small_data() -> None:
    data = [{"name": "Alice"}]
    result = await split_data_if_required(data, ENCODING)
    assert result == [data], "Expecting the data not to be split"


@pytest.mark.asyncio()
async def test_split_data_if_required_large_data() -> None:

    data = [{"name": "Alice"}] * 1_000_000  # Large dataset
    result = await split_data_if_required(data, ENCODING)
    assert len(result) > 1, "Expecting the data to be split"
