"""
- OpenAI Assistant Files Integration
  - Use WCC and Public actors actor and save content to a file.

  INPUTS: dataset_id, assistant_id, file_ids [optional], file_prefix [optional], file_name [optional]
- If a file is bigger than 2_000_000 tokens - create multiple files
- Create a file and attach it to assistant
- "update" - delete old file, create a new one and attach it to the assistant

# check assistant exists
"""


from httpx import AsyncClient

from apify import Actor


async def main() -> None:
    async with Actor:

        actor_inputs = await Actor.get_input()
        print(actor_inputs)
