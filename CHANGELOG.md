# Change Log

## 0.3.0 (2026-08-04)

- Migrate off the retired OpenAI Assistants API surface (shutdown 2026-08-26): `client.beta.vector_stores.*` -> `client.vector_stores.*`, and `openai.types.beta.vector_stores`/`openai.types.beta.VectorStore` -> `openai.types.vector_stores`/`openai.types.VectorStore`. Pin `openai = "^2"`.
- Remove the `client.beta.assistants.retrieve` lookup entirely. Splitting an oversized dataset into multiple files now happens automatically for every run, using a fixed `o200k_base` tokenizer encoding, regardless of whether `assistantId` is supplied.
- Deprecate the `assistantId` input: it is now hidden in the input editor and ignored. Supplying it logs a deprecation warning instead of looking up an Assistant; it no longer causes an early failure for an invalid/bogus value. The field is kept (accepted but unused) so existing saved inputs/integrations keep validating.
- Add a cheap byte-based pre-check before invoking tiktoken: datasets serializing to at most 5,000,000 bytes are guaranteed to be under the 5,000,000-token-per-file limit and skip tokenization entirely.
- Update README to stop instructing users to create an OpenAI Assistant, remove `assistantId` from example inputs, and point at the Responses API `file_search` tool for consuming the vector store; note that `examples/` demonstrates the retired Assistants API.

## 0.2.7 (2025-09-18)

- Update tiktoken to support the latest models.

## 0.2.6 (2025-08-15)

- Fix issue with whitespace in the input parameters.

## 0.2.5 (2025-02-12)

- Handle scenarios where the `fields` parameter is empty.
- Enable data extraction from arrays. For example, in `datasetFields`, it is now possible to extract the name from the first item using the syntax: `item[0].name`.

## 0.2.4 (2024-11-27)

- Avoid adding files to the vector store in batches, as it becomes impossible to identify failures and subsequently remove those files from OpenAI files. While this approach may be less efficient, it provides better control over which files are successfully uploaded to the OpenAI vector store.

## 0.2.3 (2024-11-26)

- Create batch files with a maximum of 500 files in batch for vector store upload.
- Update the README.md file with the Apify's badge.
- Update dependencies to the latest version

## 0.2.2 (2024-10-09)

- Add emojis to the README.md file.
- Add examples how to use the integration with OpenAI Assistant.

## 0.2.1 (2024-07-02)

- Fix issue with pagination when listing files in the OpenAI Assistant.

## 0.2.0 (2024-05-09)

- Added support to upload files to the OpenAI Assistant. The files are retrieved from the Apify's key-value store.

## 0.1.0 (2024-04-19)

- Initial release of OpenAI vector store integration
