# ruff: noqa:T201,SIM115

"""
- Create OpenAI Assistant and add tools
- Create a thread and a message
- Run the Assistant and poll for the results
- Submit tool outputs
- Get assistant answer
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from apify_client import ApifyClient
from openai import OpenAI, Stream
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput

if TYPE_CHECKING:
    from openai.types.beta import AssistantStreamEvent
    from openai.types.beta.threads import Run

client = OpenAI(api_key="YOUR-OPENAI-API-KEY")
apify_client = ApifyClient("YOUR-APIFY-API-TOKEN")

INSTRUCTIONS = """
You are a smart and helpful assistant. Maintain an expert, friendly, and informative tone in your responses.
Your task is to answer questions based on information from the internet.
Always call call_rag_web_browser function to retrieve the latest and most relevant online results.
Never provide answers based solely on your own knowledge.
For each answer, always include relevant sources whenever possible.
"""

rag_web_browser_function = {
    "type": "function",
    "function": {
        "name": "call_rag_web_browser",
        "description": "Query Google search, scrape the top N pages from the results, and returns their cleaned content as markdown",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Use regular search words or enter Google Search URLs. "},
                "maxResults": {"type": "integer", "description": "The number of top organic search results to return and scrape text from"}
            },
            "required": ["query"]
        }
    }
}

my_assistant = client.beta.assistants.retrieve("asst_7GXx3q9lWLmhSf9yexA7J1WX")


def call_rag_web_browser(query: str, max_results: int) -> list[dict]:
    """
    Query Google search, scrape the top N pages from the results, and returns their cleaned content as markdown.
    First start the Actor and wait for it to finish. Then fetch results from the Actor run's default dataset.
    """
    actor_call = apify_client.actor("apify/rag-web-browser").call(run_input={"query": query, "maxResults": max_results})
    return apify_client.dataset(actor_call["defaultDatasetId"]).list_items().items


def submit_tool_outputs(run_: Run) -> Run | Stream[AssistantStreamEvent]:
    """ Submit tool outputs to continue the run """
    tool_output = []
    for tool in run_.required_action.submit_tool_outputs.tool_calls:
        if tool.function.name == "call_rag_web_browser":
            d = json.loads(tool.function.arguments)
            output = call_rag_web_browser(query=d["query"], max_results=d["maxResults"])
            tool_output.append(ToolOutput(tool_call_id=tool.id, output=json.dumps(output)))
            print("RAG-Web-Browser added as a tool output.")

    return client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=run_.thread_id, run_id=run_.id, tool_outputs=tool_output)


# Runs are asynchronous, which means you'll want to monitor their status by polling the Run object until a terminal status is reached.
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id, role="user", content="What are the latest LLM news?"
)

# Run with assistant and poll for the results
run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=my_assistant.id)

if run.status == "requires_action":
    run = submit_tool_outputs(run)

print("Assistant response:")
for m in client.beta.threads.messages.list(thread_id=run.thread_id):
    print(m.content[0].text.value)

# Delete the thread
client.beta.threads.delete(thread.id)
