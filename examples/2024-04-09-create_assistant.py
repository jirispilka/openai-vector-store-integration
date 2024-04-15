import json
import os
from pathlib import Path

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

PATH = Path(__file__).parent.parent / "data"
FILE_PUBLIC_ACTORS = PATH / "dataset_public-actors-lister-apify-advisor_2024-04-09_19-23-55-381.json"
FILE_APIFY_COM = PATH / "dataset_apify-advisor-gpt_2024-04-10_14-34-47-759.json"

os.environ["OPENAI_API_KEY"] = ""

client = OpenAI()


def openai_assistant_files_actor(data: list[dict], assistant_id: str, file_ids: list[str] | None = None):
    """Add files and attach them to the Assistant."""

    if not assistant_id:
        print("assistant_id is required")
        return

    if not client.beta.assistants.retrieve(assistant_id):
        print("assistant_id does not exist")
        return

    file_ids_to_delete = file_ids

    try:
        file = client.files.create(file=("test.json", json.dumps(data).encode("utf-8")), purpose="assistants")
        created_file = client.beta.assistants.files.create(assistant_id, file_id=file.id)
        print(created_file)
        client.beta.assistants.files.create(assistant_id, file_id=file.id)
    except Exception as e:
        print(e)
    finally:
        if file_ids_to_delete:
            for file_id in file_ids_to_delete:
                d = client.files.delete(file_id)
                print(d)
                print(f"Deleted file {file_id}")


def openai_assistant_actor(
    name: str | None = None,
    instructions: str | None = None,
    model: str = "gpt-3.5-turbo",
    file_ids: list[str] | None = None,
    assistant_id: str | None = None,
    query: str | None = None,
) -> tuple[str | None, str | None]:

    # create assistant
    if name and instructions and model:
        assistant_id = create_assistant(name, model, instructions, file_ids)

    # query assistant
    response = ""
    if assistant_id and query:
        response = query_assistant(assistant_id, query)

    return assistant_id, response


def create_assistant(name: str, model: str, instructions: str, file_ids: list[str] | None = None) -> str:
    try:
        assistant = client.beta.assistants.create(
            instructions=instructions,
            name=name,
            model=model,
            file_ids=file_ids,
            tools=[{"type": "retrieval"}],
        )
        print("Created assistant: ", assistant)
        return assistant.id
    except Exception as e:
        print(e)


def query_assistant(assistant_id: str, query: str):
    try:
        run = client.beta.threads.create_and_run_poll(
            assistant_id=assistant_id, thread={"messages": [{"role": "user", "content": query}]}
        )
        message_final = list(client.beta.threads.messages.list(thread_id=run.thread_id))[0]
        response = "\n".join([_m.text.value for _m in message_final.content])
        client.beta.threads.delete(run.thread_id)
        return response
    except Exception as e:
        print(e)


if __name__ == "__main__":

    # _id = openai_assistant_actor(name="jiri-test-apify-advisor", instructions=INSTRUCTIONS, model="gpt-3.5-turbo")
    # print(_id)

    import pandas as pd

    df = pd.read_csv(
        "/home/jirka/dokumenty/apify/apify-adviser/Apify-Advisor-sales-new-leads-Experiments-15.4-latest.csv"
    )
    # print(df["Message"])

    # _id = "asst_vBkIISZnPDB5d16M2rf99wDI"
    # df["Apify Advisor - PROMPT_V3"] = ""
    # df["latency [sec]"] = 0
    # for index, row in df.iterrows():
    #     print("Question:", row["Message"])
    #     st = time.time()
    #     r = query_assistant(_id, row["Message"])
    #     et = time.time()
    #     df.at[index, "Apify Advisor - PROMPT_V3"] = r
    #     df.at[index, "latency [sec]"] = et - st
    #     print("Response", r)
    #     print(df)
    #
    # df.to_csv(
    #     "/home/jirka/dokumenty/apify/apify-adviser/Apify-Advisor-sales-new-leads-Experiments-15.4-latest-2.csv",
    #     index=False,
    # )
