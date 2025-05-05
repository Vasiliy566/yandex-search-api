import asyncio
import base64
import logging
import time
from typing import Dict, Optional

import httpx

from . import YandexSearchAPIClient, IamTokenResponse, SearchType, Region, ResponseFormat
from .exceptions import YandexSearchAPIError, YandexSearchTimeoutError, YandexAuthError

logging.getLogger('YandexSearchApi').addHandler(logging.NullHandler())
logger = logging.getLogger('YandexSearchApi')



class AsyncYandexSearchAPIClient(YandexSearchAPIClient):
    """
    Asynchronous Yandex Search API client for Python using httpx
    """

    def __init__(
            self,
            folder_id: str,
            oauth_token: str,
    ):
        """
        Initialize the async client

        Args:
            folder_id: Yandex Cloud folder ID
            oauth_token: Yandex OAuth token
        """
        self.folder_id = folder_id
        self.oauth_token = oauth_token
        self._client = httpx.AsyncClient()
        self.__iam_token_data: Optional[IamTokenResponse] = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the httpx client"""
        await self._client.aclose()

    @property
    async def _iam_token(self) -> str:
        if self.__iam_token_data is None or self.__iam_token_data.expired():
            self.__iam_token_data = await self._get_iam_token_from_oauth(self.oauth_token)
            logger.debug(f"IAM token is expired, renew: {self.__iam_token_data.expired()}")
        return self.__iam_token_data.iamToken

    async def _get_iam_token_from_oauth(self, oauth_token: str) -> IamTokenResponse:
        """
        Convert OAuth token to IAM token asynchronously

        Args:
            oauth_token: Yandex OAuth token

        Returns:
            IAM token response

        Raises:
            YandexAuthError: If token conversion fails
        """
        try:
            response = await self._client.post(
                self.IAM_TOKEN_URL,
                json={"yandexPassportOauthToken": oauth_token},
                timeout=10
            )
            response.raise_for_status()
            return IamTokenResponse.model_validate(response.json())
        except Exception as e:
            raise YandexAuthError(f"Failed to get IAM token from OAuth: {str(e)}")

    async def search(
            self,
            query_text: str,
            *,
            search_type: SearchType = SearchType.RUSSIAN,
            region: Region = Region.RUSSIA,
            page: int = 0,
            n_links: int = 10,
            response_timeout: int = 5,
    ) -> str:
        """
        Perform an asynchronous search

        Args:
            query_text: Search query text
            search_type: Type of search (default: RUSSIAN)
            region: Search region (default: RUSSIA)
            page: Page number (default: 0)
            n_links: Number of results to return (default: 10)
            response_timeout: Timeout for the initial request (default: 5)

        Returns:
            Operation ID

        Raises:
            YandexSearchAPIError: If the search request fails
        """
        headers = {
            "Authorization": f"Bearer {await self._iam_token}",
            "Content-Type": "application/json"
        }

        body = {
            "query": {
                "searchType": search_type.value,
                "queryText": query_text,
                "page": page,
            },
            "groupSpec": {
                "groupsOnPage": n_links,
            },
            "region": region.value,
            "l10N": "ru",
            "folderId": self.folder_id,
            "responseFormat": ResponseFormat.XML.value,
        }

        try:
            response = await self._client.post(
                self.BASE_URL,
                headers=headers,
                json=body,
                timeout=response_timeout
            )
            response.raise_for_status()
            return response.json()["id"]
        except Exception as e:
            raise YandexSearchAPIError(f"Search request failed: {str(e)}")

    async def _check_operation_status(self, operation_id: str) -> Dict:
        """
        Check the status of a search operation asynchronously

        Args:
            operation_id: Operation ID returned by search()

        Returns:
            Dictionary with operation status

        Raises:
            YandexSearchAPIError: If the API request fails
        """
        headers = {
            "Authorization": f"Bearer {await self._iam_token}"
        }

        try:
            response = await self._client.get(
                f"{self.OPERATION_URL}{operation_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise YandexSearchAPIError(f"Status check failed: {str(e)}")

    async def get_search_results(self, operation_id: str) -> str:
        """
        Get the search results when operation is complete asynchronously

        Args:
            operation_id: Operation ID returned by search()

        Returns:
            Decoded search results (XML)

        Raises:
            YandexSearchAPIError: If the operation failed or no data available
        """
        status = await self._check_operation_status(operation_id)

        if not status.get("done", False):
            raise YandexSearchAPIError("No response data available")

        if "response" not in status or "rawData" not in status["response"]:
            raise YandexSearchAPIError("No response data available")

        try:
            return base64.b64decode(status["response"]["rawData"]).decode('utf-8')
        except Exception as e:
            raise YandexSearchAPIError(f"Failed to decode results: {str(e)}")

    async def search_and_wait(
            self,
            query_text: str,
            *,
            search_type: SearchType = SearchType.RUSSIAN,
            max_wait: int = 300,
            interval: int = 1,
            n_links: int = 10,
    ) -> str:
        """
        Perform a search and wait for results asynchronously

        Args:
            query_text: Search query text
            search_type: Type of search (default: RUSSIAN)
            max_wait: Maximum time to wait in seconds (default: 300)
            interval: Time between checks in seconds (default: 1)
            n_links: Number of results to return (default: 10)

        Returns:
            XML search results

        Raises:
            YandexSearchTimeoutError: If timeout is reached
            YandexSearchAPIError: If any API error occurs
        """
        operation_id = await self.search(
            query_text,
            search_type=search_type,
            n_links=n_links
        )
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                status = await self._check_operation_status(operation_id)
                if status.get("done", False):
                    return await self.get_search_results(operation_id)
                await asyncio.sleep(interval)
            except YandexSearchAPIError as e:
                raise e

        raise YandexSearchTimeoutError(f"Timeout waiting for search results after {max_wait} seconds")

    async def get_links(
            self,
            query_text: str,
            search_type: SearchType = SearchType.RUSSIAN,
            n_links: int = 10,
            max_wait: int = 300,
            interval: int = 1,
    ) -> list[str]:
        """
        Get search result links asynchronously

        Args:
            query_text: Search query text
            search_type: Type of search (default: RUSSIAN)
            n_links: Number of results to return (default: 10)
            max_wait: Maximum time to wait in seconds (default: 300)
            interval: Time between checks in seconds (default: 1)

        Returns:
            List of URLs from search results
        """
        results = await self.search_and_wait(
            query_text,
            search_type=search_type,
            n_links=n_links,
            max_wait=max_wait,
            interval=interval
        )
        links = self._extract_yandex_search_links(results)
        if len(links) != n_links:
            logger.warning(f"Found {len(links)} links but expected {n_links} links.")
        return links
