import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from xml.etree.ElementTree import Element, SubElement

import pytest

from yandex_search_api import YandexSearchAPIClient, IamTokenResponse, YandexSearchAPIError


@pytest.fixture
def client():
    return YandexSearchAPIClient(folder_id="test_folder_id", oauth_token="test_oauth_token")


@pytest.fixture(autouse=True)
def mock_yandex_auth(requests_mock):
    requests_mock.post(YandexSearchAPIClient.IAM_TOKEN_URL,
                       json={'expiresAt': str(datetime.now(tz=timezone.utc) + timedelta(days=1)), "iamToken": "test_iam_token"})


@pytest.fixture
def mock_yandex_auth_expired(requests_mock):
    requests_mock.post(YandexSearchAPIClient.IAM_TOKEN_URL,
                       json={'expiresAt': str(datetime.now(tz=timezone.utc) - timedelta(days=1)), "iamToken": "test_iam_token"})


@pytest.fixture
def mock_yandex_search(requests_mock):
    requests_mock.post(YandexSearchAPIClient.BASE_URL,
                       json={'id': "test_operation_id"})

def test_iam_token_not_expired():
    future_expiry = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    token = IamTokenResponse(expiresAt=future_expiry, iamToken="test_token")
    assert not token.expired()


def test_iam_token_expired():
    past_expiry = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    token = IamTokenResponse(expiresAt=past_expiry, iamToken="test_token")
    assert token.expired()


@pytest.mark.usefixtures("mock_yandex_auth")
def test_init_with_oauth_token():
    client = YandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    assert client._iam_token == "test_iam_token"


@pytest.mark.usefixtures("mock_yandex_auth_expired")
def test_token_refresh_when_expired():
    client = YandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    assert client._iam_token == "test_iam_token"


@pytest.mark.usefixtures("mock_yandex_auth", "mock_yandex_search")
def test_search_success():
    client = YandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    operation_id = client.search("test query")
    assert operation_id == "test_operation_id"


def test_get_search_results_success():
    test_data = base64.b64encode(b"test_xml_data").decode('utf-8')

    with patch.object(YandexSearchAPIClient, '_check_operation_status') as mock_check:
        mock_check.return_value = {
            "done": True,
            "response": {"rawData": test_data}
        }

        client = YandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        result = client.get_search_results("test_op_id")
        assert result == "test_xml_data"


def test_get_search_results_not_done():
    with patch.object(YandexSearchAPIClient, '_check_operation_status') as mock_check:
        mock_check.return_value = {"done": False}

        client = YandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        with pytest.raises(YandexSearchAPIError):
            client.get_search_results("test_op_id")


def test_search_and_wait_success():
    with patch.object(YandexSearchAPIClient, 'search') as mock_search, \
            patch.object(YandexSearchAPIClient, '_check_operation_status') as mock_check, \
            patch.object(YandexSearchAPIClient, 'get_search_results') as mock_get_results:
        mock_search.return_value = "test_op_id"
        mock_check.return_value = {"done": True}
        mock_get_results.return_value = "test_xml_data"

        client = YandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        result = client.search_and_wait("test query")
        assert result == "test_xml_data"


def test_extract_yandex_search_links():
    # Create a mock XML structure
    root = Element('root')
    group1 = SubElement(root, 'group')
    doc1 = SubElement(group1, 'doc')
    url1 = SubElement(doc1, 'url')
    url1.text = 'http://example.com/1'

    group2 = SubElement(root, 'group')
    doc2 = SubElement(group2, 'doc')
    url2 = SubElement(doc2, 'url')
    url2.text = 'http://example.com/2'

    xml_str = '<root><group><doc><url>http://example.com/1</url></doc></group><group><doc><url>http://example.com/2</url></doc></group></root>'

    client = YandexSearchAPIClient(
        folder_id="test_folder",
        oauth_token="test_oauth"
    )
    links = client._extract_yandex_search_links(xml_str)
    assert links == ['http://example.com/1', 'http://example.com/2']


def test_get_links():
    with patch.object(YandexSearchAPIClient, 'search_and_wait') as mock_search_wait, \
            patch.object(YandexSearchAPIClient, '_extract_yandex_search_links') as mock_extract:
        mock_search_wait.return_value = "<xml>test</xml>"
        mock_extract.return_value = ['link1', 'link2']

        client = YandexSearchAPIClient(
            folder_id="test_folder",
            oauth_token="test_oauth"
        )
        links = client.get_links("test query", n_links=2)
        assert links == ['link1', 'link2']
