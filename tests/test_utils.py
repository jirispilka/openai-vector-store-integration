import json

import pytest
import tiktoken

import src.utils
from src.utils import OPENAI_MAX_TOKENS_PER_FILE, get_nested_value, split_data_if_required, split_data_into_batches


def test_get_nested_value() -> None:
    data = {"a": "v1", "c1": {"c2": "v2"}}
    assert get_nested_value(data, "a") == "v1"
    assert get_nested_value(data, "c1.c2") == "v2"
    assert get_nested_value(data, "b") == {}


@pytest.mark.integration()
def test_split_data_into_batches() -> None:
    """Marked `integration`: requires the real `cl100k_base` tiktoken encoding (via `encoding_for_model`),
    which downloads its BPE file on a cold cache. The encoding is built here, inside the test, rather than
    at module level, so plain collection/import of this module never triggers a network-dependent load.
    """
    encoding = tiktoken.encoding_for_model("gpt-4-mini")
    data = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}]
    batches = split_data_into_batches(data, 15, encoding)
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
    result = await split_data_if_required(data)
    assert result == [data], "Expecting the data not to be split"


@pytest.mark.asyncio()
@pytest.mark.integration()
async def test_split_data_if_required_large_data(monkeypatch) -> None:  # type: ignore  # noqa: ANN001
    """Exercises the real split branch, cheaply.

    `OPENAI_MAX_TOKENS_PER_FILE` also sets the byte pre-check threshold (the pre-check reuses this same
    constant), so monkeypatching it down to a small value lets a handful of items already exceed both the
    byte pre-check and the real token limit. This drives `split_data_if_required` through the genuine
    (unmocked) `tiktoken.get_encoding` + split path without tokenizing a million items, which previously
    made this test take ~15-20s.

    Marked `integration`: still requires the real `o200k_base` tiktoken encoding, which downloads its BPE
    file on a cold cache.
    """
    monkeypatch.setattr(src.utils, "OPENAI_MAX_TOKENS_PER_FILE", 20)

    data = [{"name": "Alice"}] * 50  # Small dataset, well over the patched 20-byte/20-token limit
    result = await split_data_if_required(data)

    assert len(result) > 1, "Expecting the data to be split"
    # Content round-trips: every input item appears in exactly one output batch, in the original order.
    assert [item for batch in result for item in batch] == data


@pytest.mark.integration()
@pytest.mark.asyncio()
async def test_split_data_if_required_large_bytes_low_token_density() -> None:
    """Covers the ">5,000,000 serialized bytes but <=5,000,000 tokens" input class.

    The byte pre-check only skips tiktoken when the serialized dataset is small enough that it *cannot*
    exceed the token limit. A dataset that is just over the byte threshold but has a low token density
    (e.g. ordinary repetitive English text, which tiktoken encodes at roughly one token per several bytes)
    falls through to the real tiktoken count and must land in the `else: data = [data]` arm (a single
    un-split batch), not the split branch. This test exercises that arm, which no other test reaches: the
    other split tests use highly token-dense data (many small dicts) that comfortably exceeds the token
    limit as soon as it exceeds the byte one.

    Marked `integration` (like this repo's other network-touching tests) because it requires the real
    `o200k_base` tiktoken encoding, which downloads its BPE file on a cold cache.
    """
    sentence = "The quick brown fox jumps over the lazy dog. "
    text = sentence * (OPENAI_MAX_TOKENS_PER_FILE // len(sentence) + 10)  # just over the byte threshold
    data = [{"text": text}]

    serialized_bytes = len(json.dumps(data).encode("utf-8"))
    assert serialized_bytes > OPENAI_MAX_TOKENS_PER_FILE, "Test data must exceed the byte pre-check threshold"

    result = await split_data_if_required(data)

    assert result == [data], "Expecting a single un-split batch: over the byte threshold but under the token limit"
