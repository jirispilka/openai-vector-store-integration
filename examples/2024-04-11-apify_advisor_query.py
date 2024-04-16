# pip install openai

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

assistant_id = os.getenv("ASSISTANT_ID")
query = "I need to use TikTok scraper"

client = OpenAI()

# create a thread (session) and add message
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(thread_id=thread.id, role="user", content=query)
run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=assistant_id)

# run status can be: expired, completed, failed, cancelled
# https://platform.openai.com/docs/assistants/how-it-works/run-lifecycle
if run.status == "completed":
    # messages: list - can contain "debug" messages, like "retrieving results from knowledge base"
    # take the latest message
    message_final = list(client.beta.threads.messages.list(thread_id=run.thread_id))[0]
    response = "\n".join([_m.text.value for _m in message_final.content])
    print(response)
else:
    # there needs to be some fallback message for terminal states: expired, failed, cancelled
    print(run.status)
