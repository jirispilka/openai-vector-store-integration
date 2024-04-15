# OpenAI Assistant Files Integration

The Apify OpenAI Assistant Actor allows to dynamically update the AI Assistant files.

- OpenAI Assistant Files Integration
  - Use WCC and Public actors actor and save content to a file.

  INPUTS: dataset_id, assistant_id, file_ids_to_delete [optional], file_prefix_to_delete [optional], file_name [optional]
- If a file is bigger than 2_000_000 tokens - create multiple files
- Create a file and attach it to assistant
- "update" - delete old file, create a new one and attach it to the assistant

TODO
- get also pdf files, pptx etc.
