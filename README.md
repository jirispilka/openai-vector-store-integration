# OpenAI Vector Store Integration (OpenAI Assistant)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/jirispilka/openai-vector-store-integration/blob/main/LICENSE)
[![Build & Unit Tests](https://github.com/jirispilka/openai-vector-store-integration/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/jirispilka/openai-vector-store-integration/actions/workflows/main.yml)

The Apify OpenAI Vector Store integration allows dynamic updates to the OpenAI Assistant files.
It assumes that you have already created an [OpenAI Assistant](https://platform.openai.com/docs/assistants/overview/agents) and [OpenAI Vector Store](https://platform.openai.com/docs/assistants/tools/file-search/vector-stores) and you need to regularly update the files to provide up-to-date responses.

💡 **Note**: This Actor is meant to be used together with other Actors' integration sections.
For instance, if you are using the [Website Content Crawler](https://apify.com/apify/website-content-crawler), you can activate Vector Store Files integration to save web content (including docx, pptx, pdf and other [files](https://platform.openai.com/docs/assistants/tools/file-search/supported-files)) for your OpenAI assistant.

Is there anything you find unclear or missing? Please don't hesitate to inform us by creating an issue.

## How does OpenAI Assistant Integration work?

Data for the Vector Store and Assistant are provided by various [Apify actors](https://apify.com/store) and includes web content, Docx, Pdf, Pptx, and other files.

The integration process includes:
- Loading data from an Apify Actor
- Processing the data to comply with OpenAI Assistant limits (max. 1000 files, max 5,000,000 tokens)
- Creating OpenAI files [OpenAI Files](https://platform.openai.com/docs/api-reference/files)
- [Optional] Removing existing files from the Vector Store (specified by `fileIdsToDelete` and/or `filePrefix`)
- Adding the newly created files to the vector store.
- [Optional] Deleting existing files from the OpenAI files (specified by `fileIdsToDelete` and/or `filePrefix`)

## How much does it cost?
Find the average usage cost for this actor on the [pricing page](https://apify.com/pricing) under the `Which plan do I need?` section.
Additional costs are associated with the use of OpenAI Assistant. Please refer to their [pricing](https://openai.com/pricing) for details.

## Before you start

To utilize this integration, ensure you have:

- An OpenAI account and an `OpenAI API token`. Create a free account at [OpenAI](https://beta.openai.com/).
- Created an [OpenAI Vector Store](https://platform.openai.com/docs/assistants/tools/file-search/vector-stores). You will need `vectorStoreId` to run this integration.
- Created an [OpenAI Assistant](https://platform.openai.com/docs/assistants/overview).

## Inputs

Refer to [input schema](.actor/input_schema.json) for details.

- `vectorStoreId` - OpenAI Vector Store ID
- `openaiApiKey` - OpenAI API key
- `assistantId`: The ID of an OpenAI Assistant. This parameter is required only when a file exceeds the OpenAI
   size limit of 5,000,000 tokens (as of 2024-04-23). When necessary, the model associated with the assistant is
   utilized to count tokens and split the large file into smaller, manageable segments.
- `fields` - Array of fields you want to save, e.g., `["url", "text", "metadata.title"]`.
- `fileIdsToDelete` - Delete specified file IDs from vector store as needed.
- `filePrefix` - Delete and create files using a filePrefix, streamlining vector store updates.
- `datasetId`: [Debug] Dataset ID (when running Actor as standalone without integration).
- `keyValueStoreId`: [Debug] Key Value Store ID (when running Actor as standalone without integration).
- `saveInApifyKeyValueStore`: [Debug] Save all created files in the Apify Key-Value Store to easily check and retrieve all files (this is typically used when debugging)

## Outputs

This integration saves selected fields from your Actor to the OpenAI Assistant and optionally to Actor Key Value Storage (useful for debugging).

## Want to talk to other devs or get help?

Join our [developer community on Discord](https://discord.com/invite/jyEM2PRvMU) to connect with others and discuss this and other integrations.

## Need data for your LLMs?

Utilize the Apify platform to [gather data for your large language models](https://apify.com/data-for-generative-ai).
Our Actors can automatically ingest entire websites, such as customer documentation, knowledge bases, help centers,
forums, blog posts, and other information sources to train or prompt your LLMs.
Integrate Apify into your product and allow your customers to upload their content in minutes.
