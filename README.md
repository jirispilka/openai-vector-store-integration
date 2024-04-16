# OpenAI Assistant Files Integration

The Apify OpenAI Assistant integration allows dynamic updates to the OpenAI Assistant files.
It assumes that you have already created an [OpenAI Assistant](https://platform.openai.com/docs/assistants/overview/agents)
and you need to regularly update the Assistant files to provide up-to-date responses.

⚠️ **Note**: This Actor is meant to be used together with other Actors' integration sections.
For instance, if you are using the [Website Content Crawler](https://apify.com/apify/website-content-crawler),
you can enable OpenAI Assistant Files integration to store data from the web in your OpenAI assistant.

Is there anything you find unclear or missing? Please don't hesitate to inform us by creating an issue.

## How does OpenAI Assistant Integration work?

The data for the Assistant is provided from one of the many [Apify actors](https://apify.com/store).

The integration performs the following:
- Load data from an Apify Actor
- Process the data and make sure they comply with OpenAI Assistant limits (max. 20 files, max 2,000,000 tokens)
- Create OpenAI files [OpenAI Files](https://platform.openai.com/docs/api-reference/files)
- [Optional] Dissociate existing files from the Assistant (specified by `file_ids_to_delete` and/or `file_prefix`)
- Associate newly created files with the Assistant
- [Optional] Delete existing files from the OpenAI files (specified by `file_ids_to_delete` and/or `file_prefix`)

## How much does it cost?
You can find the average usage cost for this actor on the [pricing page](https://apify.com/pricing) under the `Which plan do I need?` section.
Additional costs are associated with the use of OpenAI Assistant. Please refer to their [pricing](https://openai.com/pricing) for details.

## Before you start

To utilize this integration, ensure you have:

- An OpenAI account and an `OpenAI API token`. Create a free account at [OpenAI](https://beta.openai.com/).
- Created an [OpenAI Assistant](https://platform.openai.com/docs/assistants/overview). You will need `assistant_id` to run this integration.

## Inputs

For details refer to [input schema](.actor/input_schema.json).

- `assistant_id`: OpenAI Assistant ID
- `openai_api_key` - OpenAI API key
- `fields` - Array of fields you want to save. For example, if you want to select `url`, `text`, and `metadata.title` fields, you should set the fields to `["url", "text", "metadata.title"]`.
- `file_ids_to_delete` - Delete specified file IDs. This can be useful to delete files that are no longer needed.
- `file_prefix` - Using a file prefix streamlines the management of Assistant file updates by eliminating the need to track each file's ID. For instance, if you set the file_prefix to 'apify-advisor', the Actor will initially locate all files associated with the Assistant that have this prefix. Subsequently, it will delete these files and create new ones, also prefixed accordingly.
- `dataset_id`: [Debug] Dataset ID (when running Actor as standalone without integration).

Fields `fields`, `metadata_values`, and `metadata_fields` support dot notation. For example, if you want to push `name` field from `user` object, you should set `fields` to `["user.name"]`.

## Outputs

This integration will save the selected fields from your Actor to the OpenAI Assistant.
It will also save the files to Actor Key Value Storage.

## Want to talk to other devs or get help?

Join our [developer community on Discord](https://discord.com/invite/jyEM2PRvMU) to connect with other users and discuss this and other integrations.

## Need data for your LLMs?

You can also use the Apify platform to [gather data for your large language models](https://apify.com/data-for-generative-ai). We have Actors to ingest entire websites automatically.
Gather customer documentation, knowledge bases, help centers, forums, blog posts, and other sources of information to train or prompt your LLMs.
Integrate Apify into your product and let your customers upload their content in minutes.
