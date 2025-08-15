# Change Log

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
