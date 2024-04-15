import json

import tiktoken
from apify import Actor

OPENAI_MAX_FILES = 20
OPENAI_MAX_TOKENS_PER_FILE = 2_000_000


async def split_data_if_required(data: list, encoding: tiktoken.core.Encoding) -> list | None:
    """Split data if number of tokens is larger than OpenAI's limits."""

    nr_tokens = len(encoding.encode(json.dumps(data)))
    Actor.log.debug("Number of tokens in dataset %s", nr_tokens)
    if nr_tokens > OPENAI_MAX_TOKENS_PER_FILE * OPENAI_MAX_FILES:
        await Actor.fail(
            status_message=f"Number of tokens in a dataset exceeds OpenAI Assistants limits "
            f"Max token per file {OPENAI_MAX_TOKENS_PER_FILE}, "
            f"max files: {OPENAI_MAX_FILES}"
        )
        return
    if nr_tokens > OPENAI_MAX_TOKENS_PER_FILE:
        Actor.log.debug(
            "Number of tokens in dataset tokens in dataset %s is larger than OpenAI "
            "limit %s the data needs to be split into multiple files",
            nr_tokens,
            OPENAI_MAX_TOKENS_PER_FILE,
        )
        data = split_data_into_batches(data, max_tokens=OPENAI_MAX_TOKENS_PER_FILE, encoding=encoding)
        Actor.log.debug("The data were split into batches %s", len(data))
    else:
        data = [data]
    return data


def split_data_into_batches(data: list, max_tokens: int, encoding: tiktoken.core.Encoding):
    """
    Splits a list of items into batches where the total size of each batch, measured in tokens,
    does not exceed a specified maximum.

    Alternatively one can split the entire string but that might break json

    Args:
    - v (list): The list of items to be batched.
    - max_tokens (int): The maximum number of tokens that each batch can contain.

    Returns:
    - list: A list of lists, where each sublist represents a batch of items. Each batch's combined token count does not exceed the specified maximum.

    Example:
    >>> d = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Carol"}]
    >>> encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    >>> batches = split_data_into_batches(d, 15, encoding)
    >>> print(batches)
    [[{'name': 'Alice'}, {'name': 'Bob'}], [{'name': 'Carol'}]]
    """

    all_batches = []
    batch_tok, batch_start = 0, 0
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

    return all_batches


if __name__ == "__main__":

    import apify_client

    dataset_id = "fLR7roVL7yaMXlBYW"
    fields = None

    client_ = apify_client.ApifyClient()
    v_ = client_.dataset(dataset_id).list_items(clean=True, fields=fields).items

    encoding_ = tiktoken.encoding_for_model("gpt-3.5-turbo")

    b_ = split_data_into_batches(v_, 20_000, encoding_)
    for ii, v_ in enumerate(b_):
        print(f"batch {ii}: {len(v_)}, tokens: {len(encoding_.encode(json.dumps(v_)))}")
