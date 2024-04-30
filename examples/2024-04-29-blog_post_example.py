"""
- Create OpenAI Assistant
- Create Vector Store
- Add file to OpenAI files and add it to the Vector Store
- Update the Assistant with the Vector Store
"""

from pathlib import Path

from openai import OpenAI

client = OpenAI(api_key="YOUR OPENAI API KEY")

my_assistant = client.beta.assistants.create(
    instructions="As a customer support agent at Apify, your role is to assist customers "
    "with their web data extraction or automation needs.",
    name="Sales Advisor",
    tools=[{"type": "file_search"}],
    model="gpt-3.5-turbo",
)
print(my_assistant)

PATH = Path().resolve() / "data"
FILE_APIFY_COM = PATH / "dataset_apify-web.json"

# Create a file
file = client.files.create(file=open("dataset_apify-web.json", "rb"), purpose="assistants")

# Create a vector store
vector_store = client.beta.vector_stores.create(name="Sales Advisor")

# Add the file to vector store
vs_file = client.beta.vector_stores.files.create_and_poll(
    vector_store_id=vector_store.id,
    file_id=file.id,
)
print(vs_file.status)

# Update the assistant to use the new Vector Store
assistant = client.beta.assistants.update(
    assistant_id=my_assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

# Create a thread and a message
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id, role="user", content="How can I scrape a website using Apify?"
)

# Run with assistant and poll for the results
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id,
    tool_choice={"type": "file_search"}
)

for m in client.beta.threads.messages.list(thread_id=run.thread_id):
    print(m.content[0].text.value)
