# Yandex Search API Client

A Python client for interacting with Yandex's Search API, providing easy access to Yandex search results programmatically.

## Features

- Perform searches using Yandex's Search API
- Retrieve search results in XML format
- Extract URLs from search results
- Automatic IAM token management
- Configurable search parameters (region, search type, number of results)
- Asynchronous operation with timeout handling


## Installation

```bash
pip install yandex-search-api
```

## Usage

### Basic Example

```python
import logging
from yandex_search_api import YandexSearchAPIClient
from yandex_search_api.client import SearchType


def main():
    # Initialize client with your credentials
    client = YandexSearchAPIClient(
        folder_id="your_folder_id",
        oauth_token="your_oauth_token"
    )
    # How to get folder_id: https://yandex.cloud/en-ru/docs/resource-manager/operations/folder/get-id
    # How to get  oauth_token:  https://yandex.cloud/en-ru/docs/iam/concepts/authorization/oauth-token

    links = client.get_links(
        query_text="Python library for yandex search",
        search_type=SearchType.RUSSIAN,
        n_links=5
    )
    
    print("Search results:", links)

if __name__ == '__main__':
    main()
```

### Advanced Usage

```python
# Perform a search and get raw XML results
operation_id = client.search(
    query_text="Advanced search example",
    search_type=SearchType.INTERNATIONAL,
    region=Region.UKRAINE,
    n_links=20
)

# Wait for results and get XML
xml_results = client.get_search_results(operation_id)

# Or use the convenience method that waits automatically
xml_results = client.search_and_wait(
    query_text="Another example",
    max_wait=120,  # seconds
    interval=5     # seconds between checks
)
```

## Configuration

### Required Credentials

1. **Folder ID**: Your Yandex Cloud folder ID  https://yandex.cloud/en-ru/docs/resource-manager/operations/folder/get-id
2. **OAuth Token**: Your Yandex OAuth token  https://yandex.cloud/en-ru/docs/iam/concepts/authorization/oauth-token


### Search Parameters

- `search_type`: 
  - `SearchType.RUSSIAN` (default)
  - `SearchType.TURKISH`
  - `SearchType.INTERNATIONAL`
  
- `region`:
  - `Region.RUSSIA` (default)
  - `Region.UKRAINE`
  - `Region.BELARUS`
  - `Region.KAZAKHSTAN`

- `n_links`: Number of results to return (default: 10)
- `page`: Page number (default: 0)
- `max_wait`: Maximum time to wait for results in seconds (default: 300)
- `interval`: Time between operation status checks in seconds (default: 1)

## Logging

The library uses Python's logging module with logger name `YandexSearchApi`. Configure logging as needed:

```python
import logging
logging.getLogger('YandexSearchApi').setLevel(logging.DEBUG)
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
