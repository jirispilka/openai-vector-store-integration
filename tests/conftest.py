from typing import AsyncGenerator

import openai
import pytest
from dotenv import load_dotenv
from openai.types import FileObject
from openai.types.beta import VectorStore

load_dotenv()

client = openai.AsyncClient()

FILE_PREFIX = "unittest_"


@pytest.fixture
async def vector_store_fixture() -> AsyncGenerator[VectorStore, None]:
    vector_store = await client.beta.vector_stores.create(name="unittest_vector_store")
    yield vector_store
    await client.beta.vector_stores.delete(vector_store.id)


@pytest.fixture
async def file_fixture() -> AsyncGenerator[FileObject, None]:
    filename = f"{FILE_PREFIX}file.txt"
    filedata = b"Hello, OpenAI!"

    file = await client.files.create(file=(filename, filedata), purpose="assistants")
    yield file
    await client.files.delete(file.id)
