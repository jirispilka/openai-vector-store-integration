# OpenAI Vector Store Integration (OpenAI Assistant)

[![OpenAI Vector Store Integration](https://apify.com/actor-badge?actor=jiri.spilka/openai-vector-store-integration)](https://apify.com/jiri.spilka/openai-vector-store-integration)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/jirispilka/openai-vector-store-integration/blob/main/LICENSE)
[![Build & Unit Tests](https://github.com/jirispilka/openai-vector-store-integration/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/jirispilka/openai-vector-store-integration/actions/workflows/main.yml)


The Apify [OpenAI Vector Store integration](https://apify.com/jiri.spilka/openai-vector-store-integration) uploads data from Apify Actors to the OpenAI Vector Store (connected to the OpenAI Assistant).
It assumes that you have already created a [OpenAI Vector Store](https://platform.openai.com/docs/assistants/tools/file-search/vector-stores) and you need to regularly update the files to provide up-to-date responses.

💡 **Note**: This Actor is meant to be used together with other Actors' integration sections.
For instance, if you are using the [Website Content Crawler](https://apify.com/apify/website-content-crawler), you can activate Vector Store Files integration to save web content (including docx, pptx, pdf and other [files](https://platform.openai.com/docs/assistants/tools/file-search/supported-files)) for your OpenAI assistant.

Is there anything you find unclear or missing? Please don't hesitate to inform us by creating an issue.

You can easily run the [OpenAI Vector Store Integration](https://apify.com/jiri.spilka/openai-vector-store-integration) at the Apify Platform.

Read a detailed guide in the [documentation](https://docs.apify.com/platform/integrations/openai-assistants#save-data-into-openai-vector-store-and-use-it-in-the-assistant) or in blogpost [How we built an enterprise support assistant using OpenAI and the Apify platform](https://blog.apify.com/enterprise-support-openai-assistant/).

## ֎ How does OpenAI Assistant Integration work?

Data for the Vector Store and Assistant are provided by various [Apify actors](https://apify.com/store) and can include web content, Docx, Pdf, Pptx, and other files.

The following image illustrates the Apify-OpenAI Vector Store integration:

![Apify-OpenAI Vector Store integration](https://raw.githubusercontent.com/jirispilka/openai-vector-store-integration/refs/heads/main/docs/openai-vector-store-integration-2.png)

The integration process includes:
- Loading data from an Apify Actor
- Processing the data to comply with OpenAI Assistant limits (max. 1000 files, max 5,000,000 tokens)
- Creating [OpenAI Files](https://platform.openai.com/docs/api-reference/files)
- _[Optional]_ Removing existing files from the Vector Store (specified by `fileIdsToDelete` and/or `filePrefix`)
- Adding the newly created files to the vector store.
- _[Optional]_ Deleting existing files from the OpenAI files (specified by `fileIdsToDelete` and/or `filePrefix`)

## 💰 How much does it cost?

Find the average usage cost for this actor on the [pricing page](https://apify.com/pricing) under the `Which plan do I need?` section.
Additional costs are associated with the use of OpenAI Assistant. Please refer to their [pricing](https://openai.com/pricing) for details.

Since the integration is designed to upload entire dataset as a OpenAI file, the cost is minimal, typically less than $0.01 per run.

## ✅ Before you start

To use this integration, ensure you have:

- An OpenAI account and an `OpenAI API KEY`. Create a free account at [OpenAI](https://beta.openai.com/).
- Created an [OpenAI Vector Store](https://platform.openai.com/docs/assistants/tools/file-search/vector-stores). You will need `vectorStoreId` to run this integration.
- _[Optional]_ Created an [OpenAI Assistant](https://platform.openai.com/docs/assistants/overview).

## ➡️ Inputs

Refer to [input schema](.actor/input_schema.json) for details.

- `vectorStoreId` - OpenAI Vector Store ID
- `openaiApiKey` - OpenAI API key
- `assistantId`: The ID of an OpenAI Assistant. This parameter is required only when a file exceeds the OpenAI
   size limit of 5,000,000 tokens (as of 2024-04-23). When necessary, the model associated with the assistant is
   utilized to count tokens and split the large file into smaller, manageable segments.
- `datasetFields` - Array of datasetFields you want to save, e.g., `["url", "text", "metadata.title"]`.
- `filePrefix` - Delete and create files using a filePrefix, streamlining vector store updates.
- `fileIdsToDelete` - Delete specified file IDs from vector store as needed.
- `datasetId`: _[Debug]_ Apify's Dataset ID (when running Actor as standalone without integration).
- `keyValueStoreId`: _[Debug]_ Apify's Key Value Store ID (when running Actor as standalone without integration).
- `saveInApifyKeyValueStore`: _[Debug]_ Save all created files in the Apify Key-Value Store to easily check and retrieve all files (this is typically used when debugging)

## ⬅️ Outputs

This integration saves selected `datasetFields` from your Actor to the OpenAI Assistant and optionally to Actor Key Value Storage (useful for debugging).

## 💾 Save data from Website Content Crawler to OpenAI Vector Store

To use this integration, you need an OpenAI account and an `OpenAI API KEY`.
Additionally, you need to create an OpenAI Vector Store (`vectorStoreId`).

The Website Content Crawler can deeply crawl websites and save web page content to Apify's dataset.
It also stores files such as PDFs, PPTXs, and DOCXs.
A typical run crawling `https://platform.openai.com/docs/assistants/overview` includes the following dataset fields (truncated for brevity):

```json
[
  {
    "url": "https://platform.openai.com/docs/assistants/overview",
    "text": "Assistants overview - OpenAI API\nThe Assistants API allows you to build AI assistants within your own applications ..."
  },
  {
    "url": "https://platform.openai.com/docs/assistants/overview/step-1-create-an-assistant",
    "text": "Assistants overview - OpenAI API\n An Assistant has instructions and can leverage models, tools, and files to respond to user queries ..."
  }
]
```
Once you have the dataset, you can store the data in the OpenAI Vector Store.
Specify which fields you want to save to the OpenAI Vector Store, e.g., `["text", "url"]`.

```json
{
  "assistantId": "YOUR-ASSISTANT-ID",
  "datasetFields": ["text", "url"],
  "openaiApiKey": "YOUR-OPENAI-API-KEY",
  "vectorStoreId": "YOUR-VECTOR-STORE-ID"
}
```

### 🔄 Update existing files in the OpenAI Vector Store

There are two ways to update existing files in the OpenAI Vector Store.
You can either delete all files with a specific prefix or delete specific files by their IDs.
It is more convenient to use the `filePrefix` parameter to delete and create files with the same prefix.
In the first run, the integration will save all the files with the prefix `openai_assistant_`.
In the next run, it will delete all the files with the prefix `openai_assistant_` and create new files.

The settings for the integration are as follows:
```json
{
  "assistantId": "YOUR-ASSISTANT-ID",
  "datasetFields": ["text", "url"],
  "filePrefix": "openai_assistant_",
  "openaiApiKey": "YOUR-OPENAI-API-KEY",
  "vectorStoreId": "YOUR-VECTOR-STORE-ID"
}
```

## 📦 Save Amazon Products to OpenAI Vector Store

You can also save Amazon products to the OpenAI Vector Store.
Again, you need to have an OpenAI account and an `OpenAI API KEY` with a created OpenAI Vector Store (`vectorStoreId`).

To scrape Amazon products, you can use the [Amazon Product Scraper](https://apify.com/junglee/amazon-crawler) Actor.

Let's say that you want to scrape "Apple Watch" and store all the scraped data in the OpenAI Assistant.
For the product URL `https://www.amazon.com/s?k=apple+watch`, the scraper can yield the following results (truncated for brevity):

```json
[
  {
    "title": "Apple Watch Ultra 2 [GPS + Cellular 49mm] Smartwatch with Rugged Titanium Case ....",
    "asin": "B0CSVGK51Y",
    "brand": "Apple",
    "stars": 4.7,
    "reviewsCount": 357,
    "thumbnailImage": "https://m.media-amazon.com/images/I/81pjcQFaDJL.__AC_SY445_SX342_QL70_FMwebp_.jpg",
    "price": {
      "value": 794,
      "currency": "$"
    },
    "url": "https://www.amazon.com/dp/B0CSVGK51Y"
  }
]
```

You can easily save the data to the OpenAI Vector Store by creating an integration (in the Amazon Product Scraper integration section) and specifying the fields you want to save:

```json
{
  "assistantId": "YOUR-ASSISTANT-ID",
  "datasetFields": ["title", "brand", "stars", "reviewsCount", "thumbnailImage", "price.value", "price.currency", "url"],
  "openaiApiKey": "YOUR-OPENAI-API-KEY",
  "vectorStoreId": "YOUR-VECTOR-STORE-ID"
}
```

## ⓘ Limitations

- Crawled files, such as PDFs, PPTXs, and DOCXs, are saved in the OpenAI Vector Store as single files and uploaded one by one. While this approach is inefficient, it allows for better error handling and the ability to log detailed error messages.
- OpenAI can process text-based PDF files but cannot handle PDF images or scanned PDFs. For the latter, you need to use OCR to extract text from images.
