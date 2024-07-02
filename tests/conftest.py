from typing import AsyncGenerator
import random

import openai
import pytest
from dotenv import load_dotenv
from openai.types import FileObject
from openai.types.beta import VectorStore
from string import ascii_lowercase

load_dotenv()

client = openai.AsyncClient()


@pytest.fixture(scope="function")
async def vector_store_fixture() -> AsyncGenerator[VectorStore, None]:

    suffix = "".join(random.choices(ascii_lowercase, k=8))
    vector_store = await client.beta.vector_stores.create(name=f"unittest_vector_store_{suffix}")
    yield vector_store
    await client.beta.vector_stores.delete(vector_store.id)


@pytest.fixture(scope="function")
async def file_fixture() -> AsyncGenerator[FileObject, None]:

    s = "".join(random.choices(ascii_lowercase, k=4))
    filename = f"unittest_{s}__file.txt"
    filedata = b"Hello, OpenAI!"

    file = await client.files.create(file=(filename, filedata), purpose="assistants")
    yield file
    await client.files.delete(file.id)
