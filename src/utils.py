from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import tiktoken

from apify import Actor

OPENAI_MAX_FILES = 10_000
OPENAI_MAX_TOKENS_PER_FILE = 5_000_000


def get_nested_value(data: dict | list | Any, keys: str) -> Any:  # noqa:PLR0912
    """
    Extracts a nested value from a dictionary (or list), supporting nested dicts and lists.

    Examples:
      >>> get_nested_value({"a": "v1", "c1": {"c2": "v2"}}, "c1.c2")
      'v2'
      >>> get_nested_value({"cards": [{"name": "card1"}, {"name": "card2"}]}, "cards[0].name")
      'card1'
      >>> get_nested_value({"cards": [{"name": "card1"}, {"name": "card2"}]}, "cards[:].name")
      'card1 card2'
    """
    # Split the key path; note that this simple split won't handle dots in keys.
    keys_parts = keys.split(".")
    current: Any = data

    for i, part in enumerate(keys_parts):
        if current is None:
            return {}

        # Handle list indexing if '[' and ']' are present in the key part.
        if "[" in part and "]" in part:
            try:
                base, rest = part.split("[", 1)
                index_str = rest.rstrip("]")
            except ValueError:
                return {}

            # If there's a base key, fetch it from the current dict.
            if base:
                if isinstance(current, dict):
                    current = current.get(base)
                else:
                    return {}
            # At this point, current should be a list.
            if not isinstance(current, list):
                return {}

            if index_str == ":":
                # For a slice, process the remaining keys (if any) on each list element.
                remaining_keys = ".".join(keys_parts[i + 1 :])
                if remaining_keys:
                    # Gather values from each item where the nested lookup is successful.
                    values = [
                        str(get_nested_value(item, remaining_keys))
                        for item in current
                        if get_nested_value(item, remaining_keys) not in (None, {}, "")
                    ]
                    return " ".join(values)
                # If no further keys, join all items as strings.
                return " ".join(map(str, current))
            try:
                idx = int(index_str)
            except ValueError:
                return {}
            try:
                current = current[idx]
            except (IndexError, TypeError):
                return {}
        else:
            # Handle simple dictionary key access.
            try:
                if isinstance(current, dict):
                    current = current[part]
                else:
                    return {}
            except (KeyError, TypeError):
                return {}
    return current


async def split_data_if_required(data: list, encoding: tiktoken.core.Encoding) -> list:
    """Split data if number of tokens is larger than OpenAI's limits."""

    nr_tokens = len(encoding.encode(json.dumps(data)))
    Actor.log.debug("Number of tokens in dataset %s", nr_tokens)
    if nr_tokens > OPENAI_MAX_TOKENS_PER_FILE * OPENAI_MAX_FILES:
        await Actor.fail(
            status_message=f"Number of tokens in a dataset exceeds OpenAI Assistants limits "
            f"Max token per file {OPENAI_MAX_TOKENS_PER_FILE}, "
            f"max files: {OPENAI_MAX_FILES}"
        )
        return []
    if nr_tokens > OPENAI_MAX_TOKENS_PER_FILE:
        Actor.log.debug(
            "Number of tokens in dataset tokens in dataset %s is larger than OpenAI limit %s. Split data into multiple files",
            nr_tokens,
            OPENAI_MAX_TOKENS_PER_FILE,
        )
        data = split_data_into_batches(data, max_tokens=OPENAI_MAX_TOKENS_PER_FILE, encoding=encoding)
        Actor.log.debug("The data were split into batches %s", len(data))
    else:
        data = [data]
    return data


def split_data_into_batches(data: list, max_tokens: int, encoding: tiktoken.core.Encoding) -> list:
    """
    Splits a list of items into batches where the total size of each batch, measured in tokens,
    does not exceed a specified maximum.

    Alternatively one can split the entire string but that might break json

    Args:
    - v (list): The list of items to be batched.
    - max_tokens (int): The maximum number of tokens that each batch can contain.

    Returns:
    - list: A list of lists, where each sublist represents a batch of items. Each batch's combined token count does
            not exceed the specified maximum.

    Example:
    >>> d = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}]
    >>> enc = tiktoken.encoding_for_model("gpt-5-mini")
    >>> batches = split_data_into_batches(d, 15, enc)
    >>> print(batches)
    [[{'name': 'Alice'}, {'name': 'Bob'}], [{'name': 'Carol'}]]
    """

    all_batches = []
    batch_tok, batch_start = 0, 0
    try:
        for i, v in enumerate(data):
            t = len(encoding.encode(json.dumps(v)))
            if batch_tok + t < max_tokens:
                batch_tok += t
            else:
                if batch_tok > 0:
                    all_batches.append(data[batch_start:i])
                batch_tok, batch_start = t, i
        if batch_tok > 0:
            all_batches.append(data[batch_start:])
    except Exception as e:
        Actor.log.exception(e)

    return all_batches
