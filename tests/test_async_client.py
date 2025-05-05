import base64
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

from yandex_search_api import YandexSearchAPIError
from yandex_search_api.async_client import AsyncYandexSearchAPIClient


@pytest_asyncio.fixture
async def async_client():
    client = AsyncYandexSearchAPIClient(folder_id="test_folder_id", oauth_token="test_oauth_token")
    yield client
    await client.close()


@pytest.fixture()
def mock_yandex_auth(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=AsyncYandexSearchAPIClient.IAM_TOKEN_URL,
        json={'expiresAt': str(datetime.now(tz=timezone.utc) + timedelta(days=1)), "iamToken": "test_iam_token"}
    )


@pytest.fixture
def mock_yandex_auth_expired(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=AsyncYandexSearchAPIClient.IAM_TOKEN_URL,
        json={'expiresAt': str(datetime.now(tz=timezone.utc) - timedelta(days=1)), "iamToken": "test_iam_token"}
    )


@pytest.fixture
def mock_yandex_search(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=AsyncYandexSearchAPIClient.BASE_URL,
        json={'id': "test_operation_id"}
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_yandex_auth")
async def test_init_with_oauth_token():
    client = AsyncYandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    assert await client._iam_token == "test_iam_token"
    await client.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_yandex_auth_expired")
async def test_token_refresh_when_expired():
    client = AsyncYandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    assert await client._iam_token == "test_iam_token"
    await client.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_yandex_auth", "mock_yandex_search")
async def test_search_success():
    client = AsyncYandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    operation_id = await client.search("test query")
    assert operation_id == "test_operation_id"
    await client.close()


@pytest.mark.asyncio
async def test_get_search_results_success():
    test_data = base64.b64encode(b"test_xml_data").decode('utf-8')

    with patch.object(AsyncYandexSearchAPIClient, '_check_operation_status', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {
            "done": True,
            "response": {"rawData": test_data}
        }

        client = AsyncYandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        result = await client.get_search_results("test_op_id")
        assert result == "test_xml_data"
        await client.close()


@pytest.mark.asyncio
async def test_get_search_results_not_done():
    with patch.object(AsyncYandexSearchAPIClient, '_check_operation_status', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = {"done": False}

        client = AsyncYandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        with pytest.raises(YandexSearchAPIError):
            await client.get_search_results("test_op_id")
        await client.close()


@pytest.mark.asyncio
async def test_search_and_wait_success():
    with patch.object(AsyncYandexSearchAPIClient, 'search', new_callable=AsyncMock) as mock_search, \
            patch.object(AsyncYandexSearchAPIClient, '_check_operation_status', new_callable=AsyncMock) as mock_check, \
            patch.object(AsyncYandexSearchAPIClient, 'get_search_results', new_callable=AsyncMock) as mock_get_results:
        mock_search.return_value = "test_op_id"
        mock_check.return_value = {"done": True}
        mock_get_results.return_value = "test_xml_data"

        client = AsyncYandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        result = await client.search_and_wait("test query")
        assert result == "test_xml_data"
        await client.close()


@pytest.mark.asyncio
async def test_extract_yandex_search_links():
    xml_str = '<root><group><doc><url>http://example.com/1</url></doc></group><group><doc><url>http://example.com/2</url></doc></group></root>'

    client = AsyncYandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    links = client._extract_yandex_search_links(xml_str)
    assert links == ['http://example.com/1', 'http://example.com/2']
    await client.close()


@pytest.mark.asyncio
async def test_get_links():
    with patch.object(AsyncYandexSearchAPIClient, 'search_and_wait', new_callable=AsyncMock) as mock_search_wait, \
            patch.object(AsyncYandexSearchAPIClient, '_extract_yandex_search_links') as mock_extract:
        mock_search_wait.return_value = "<xml>test</xml>"
        mock_extract.return_value = ['link1', 'link2']

        client = AsyncYandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        links = await client.get_links("test query", n_links=2)
        assert links == ['link1', 'link2']
        await client.close()