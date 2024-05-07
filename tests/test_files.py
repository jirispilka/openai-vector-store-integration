from unittest.mock import patch

import openai
import pytest
from apify import Actor
from dotenv import load_dotenv

from src.main import create_file, delete_files

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
async def test_openai_files_integration(monkeypatch) -> None:  # type: ignore
    """Create a file, list files, retrieve file, read file, delete file."""

    filename = "unittest_file.txt"
    filedata = b"Hello, OpenAI!"

    monkeypatch.setattr(Actor, "push_data", empty)
    file = await create_file(client, filename, filedata)
    assert file is not None

    file_r = await client.files.retrieve(file.id)
    assert file_r is not None
    assert file_r.status == "processed"

    file_d = await delete_files(client, [str(file.id)])
    assert file_d is not None
    assert file_d.deleted is True
