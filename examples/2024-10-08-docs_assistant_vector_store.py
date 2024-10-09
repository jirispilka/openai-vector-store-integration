# ruff: noqa:T201,SIM115
"""
- Create OpenAI Assistant and vVector Store
- Update the assistant to use the new Vector Store
- Call Website Content Crawler and crawl docs.apify.com
- Use OpenAi Vector Store Integration to upload dataset items to the Vector Store
- Create a thread and a message and get assistant answer
"""
from apify_client import ApifyClient
from openai import OpenAI

client = OpenAI(api_key="YOUR-OPENAI-API-KEY")
apify_client = ApifyClient("YOUR-APIFY-API-TOKEN")

my_assistant = client.beta.assistants.create(
    instructions="As a customer support agent at Apify, your role is to assist customers",
    name="Support assistant",
    tools=[{"type": "file_search"}],
    model="gpt-4o-mini",
)

# Create a vector store
vector_store = client.beta.vector_stores.create(name="Support assistant vector store")

# Update the assistant to use the new Vector Store
assistant = client.beta.assistants.update(
    assistant_id=my_assistant.id,
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

run_input = {"startUrls": [{"url": "https://docs.apify.com/platform"}], "maxCrawlPages": 10, "crawlerType": "cheerio"}
actor_call_website_crawler = apify_client.actor("apify/website-content-crawler").call(run_input=run_input)

dataset_id = actor_call_website_crawler["defaultDatasetId"]

run_input_vs = {
    "datasetId": dataset_id,
    "assistantId": my_assistant.id,
    "datasetFields": ["text", "url"],
    "openaiApiKey": "YOUR-OPENAI-API-KEY",
    "vectorStoreId": vector_store.id,
}

apify_client.actor("jiri.spilka/openai-vector-store-integration").call(run_input=run_input_vs)

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

print("Assistant response:")
for m in client.beta.threads.messages.list(thread_id=run.thread_id):
    print(m.content[0].text.value)
