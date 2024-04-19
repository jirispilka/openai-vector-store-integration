"""
Creation of an Apify Advisor (OpenAI Assistant)
https://platform.openai.com/docs/assistants/overview/agents

- Create OpenAI's vector store and attach it to an Assistant
- Add files to a vector store
- Create OpenAI's assistant (with the files attached)
- Query using thread (session)
"""

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

INSTRUCTIONS = """
As a customer support agent at Apify, your role is to assist customers with their web data extraction or automation needs.
Here’s how to effectively engage:

Introduce customers to Apify Actors, tailored tools for web tasks, and suggest the most popular ones as they tend to be more reliable.
For first-time users, explain what an Apify Actor is and showcase them by name with a link, like Website Content Crawler.
If multiple Actors are relevant, mention the best fit first and indicate that more options are available in the Apify Store.
If no existing Actor fits their needs, guide them towards creating their own solution on Apify using the Crawlee library for TypeScript/Node.js or Scrapy for Python.
If they prefer not to build their own, suggest exploring custom solutions through Apify Enterprise.
Always be polite and proactive in suggesting next steps, providing valid links where applicable.
Keep responses concise and focused.
"""

load_dotenv()
client = OpenAI()

PATH = Path("/home/jirka/dokumenty/apify/apify-adviser/")
FILE_PUBLIC_ACTORS = PATH / "dataset_public-actors-lister-apify-advisor_2024-04-12-04-URL.json"
FILE_APIFY_COM = PATH / "dataset_apify-advisor-gpt_2024-04-10_14-34-47-759.json"

VECTOR_STORE_ID = "vs_l0VplHkJoVATtjA7EDLtPvL0"

# Create files
client.files.create(file=open(FILE_PUBLIC_ACTORS, "rb"), purpose="assistants")
client.files.create(file=open(FILE_APIFY_COM, "rb"), purpose="assistants")

# list all the files
for f in client.files.list():
    print(f)

file_ids = [f.id for f in client.files.list()]

vs = client.beta.vector_stores.retrieve(vector_store_id=VECTOR_STORE_ID)
print(vs)

for f in client.beta.vector_stores.files.list(vector_store_id=VECTOR_STORE_ID):
    print(f)

# ADD the files to a vector store
batch = client.beta.vector_stores.file_batches.create_and_poll(
  vector_store_id=VECTOR_STORE_ID,
  file_ids=file_ids,
)
print(batch)


for a in client.beta.assistants.list():
    print(a.id, a.name, a.created_at)

ASSISTANT_ID = "asst_JwgoDaED4YtBXeS9oZ6EeSwS"

assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
for k, v in assistant.__dict__.items():
    print(k, v)

# UPDATE Assistant
assistant = client.beta.assistants.update(assistant_id=ASSISTANT_ID, temperature=0)
for k, v in assistant.__dict__.items():
    print(k, v)

# delete files
for f in client.files.list():
    print(f"About to delete {f.filename}")
    client.files.delete(f.id)

# run thread
thread = client.beta.threads.create()

message = client.beta.threads.messages.create(
    thread_id=thread.id, role="user", content="""
    "●    Facebook
●    Twitter (X)
●    Tiktok
●    Whatsapp
●    Telegram
●    VK
●    Reddit
●    Instagram
●    Youtube
●    News Sites"
"""

)
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id,
    tool_choice={"type": "file_search"}
)

if run.status == "completed":
    for m in client.beta.threads.messages.list(thread_id=run.thread_id):
        print(m)
else:
    print(run.status)

client.beta.threads.delete(thread_id=thread.id)
