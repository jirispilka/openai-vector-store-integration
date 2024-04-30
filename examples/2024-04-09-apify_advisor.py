"""
Creation of an Apify Advisor (OpenAI Assistant)
https://platform.openai.com/docs/assistants/overview/agents

- Create OpenAI's files
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

PATH = Path().resolve() / "data"
FILE_PUBLIC_ACTORS = PATH / "dataset_apify-public-actors.json"
FILE_APIFY_COM = PATH / "dataset_apify-web.json"

client.files.create(file=open(FILE_PUBLIC_ACTORS, "rb"), purpose="assistants")
client.files.create(file=open(FILE_APIFY_COM, "rb"), purpose="assistants")

# list all the files
for f in client.files.list():
    print(f)

file_ids = [f.id for f in client.files.list()]

for a in client.beta.assistants.list():
    print(a.id, a.name, a.created_at, a.file_ids)

# create assistant
assistant = client.beta.assistants.create(
    instructions=INSTRUCTIONS,
    name="Apify Advisor",
    model="gpt-3.5-turbo",
    file_ids=file_ids,
    tools=[{"type": "retrieval"}],
)
print(assistant)


for f in client.beta.assistants.files.list(assistant_id=assistant.id):
    print(f.id)

# for f in file_ids:
#     client.beta.assistants.files.create(assistant_id=assistant.id, file_id=f)

# delete files
# for f in client.files.list():
#     print(f"About to delete {f.filename}")
#     client.files.delete(f.id)

# run thread
thread = client.beta.threads.create()

message = client.beta.threads.messages.create(
    thread_id=thread.id, role="user", content="I need to use Twitter scraper, can you help me?"

)
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id,
)

if run.status == "completed":
    for m in client.beta.threads.messages.list(thread_id=run.thread_id):
        print(m)
else:
    print(run.status)
