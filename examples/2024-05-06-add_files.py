"""
- Add a file from Apify's KV Store to OpenAI files
"""

from io import BytesIO

from apify_client import ApifyClient
from dotenv import load_dotenv
from openai import OpenAI

from src.constants import OPENAI_SUPPORTED_FILES

load_dotenv()

KV_STORE_ID = "gfHgcwJx7Ub0tQjPr"

client = OpenAI()

client_ = ApifyClient()

kv_store = client_.key_value_store(KV_STORE_ID)

for item in kv_store.list_keys().get("items", []):
    if item.get("key").split(".")[-1] in OPENAI_SUPPORTED_FILES:
        if d := kv_store.get_record_as_bytes(item.get("key")):
            file = client.files.create(file=(d["key"], BytesIO(d["value"])), purpose="assistants")
            break
