import pytest
from unittest.mock import patch, MagicMock
import base64

from yandex_search_api import YandexSearchAPIClient, YandexAuthError, YandexSearchAPIError, YandexSearchTimeoutError


@pytest.fixture
def mock_requests():
    with patch('requests.post') as mock_post, \
            patch('requests.get') as mock_get:
        yield mock_post, mock_get


@pytest.fixture
def client_with_iam():
    return YandexSearchAPIClient(folder_id="test_folder", iam_token="test_iam_token")


@pytest.fixture
def client_with_oauth():
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"iamToken": "mocked_iam_token"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        return YandexSearchAPIClient(folder_id="test_folder", oauth_token="test_oauth_token")


def test_init_with_no_token_raises_error():
    with pytest.raises(YandexAuthError):
        YandexSearchAPIClient(folder_id="test_folder")


def test_init_with_iam_token(client_with_iam):
    assert client_with_iam.iam_token == "test_iam_token"
    assert client_with_iam.folder_id == "test_folder"


def test_init_with_oauth_token(client_with_oauth):
    assert client_with_oauth.iam_token == "mocked_iam_token"


def test_get_iam_token_from_oauth_failure():
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("Connection error")
        with pytest.raises(YandexAuthError):
            YandexSearchAPIClient(folder_id="test_folder", oauth_token="bad_token")


def test_search_success(client_with_iam, mock_requests):
    mock_post, _ = mock_requests
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "test_operation_id"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    operation_id = client_with_iam.search("test query")
    assert operation_id == "test_operation_id"


def test_search_failure(client_with_iam, mock_requests):
    mock_post, _ = mock_requests
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API error")
    mock_post.return_value = mock_response

    with pytest.raises(Exception):
        client_with_iam.search("test query")


def test_check_operation_status_success(client_with_iam, mock_requests):
    _, mock_get = mock_requests
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": True}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = client_with_iam._check_operation_status("test_op_id")
    assert result == {"done": True}


def test_check_operation_status_failure(client_with_iam, mock_requests):
    _, mock_get = mock_requests
    mock_get.side_effect = Exception("API error")

    with pytest.raises(YandexSearchAPIError):
        client_with_iam._check_operation_status("test_op_id")


def test_get_search_results_success(client_with_iam, mock_requests):
    _, mock_get = mock_requests
    test_data = base64.b64encode(b"<test>data</test>").decode('utf-8')
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "done": True,
        "response": {"rawData": test_data}
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = client_with_iam.get_search_results("test_op_id")
    assert result == "<test>data</test>"


def test_get_search_results_not_done(client_with_iam, mock_requests):
    _, mock_get = mock_requests
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": False}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = client_with_iam.get_search_results("test_op_id")
    assert result is None


def test_get_search_results_no_data(client_with_iam, mock_requests):
    _, mock_get = mock_requests
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": True}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with pytest.raises(YandexSearchAPIError):
        client_with_iam.get_search_results("test_op_id")


def test_extract_yandex_search_links():
    xml_content = """
    <root>
        <group>
            <doc>
                <url>https://example.com</url>
            </doc>
        </group>
        <group>
            <doc>
                <url>https://test.com</url>
            </doc>
        </group>
    </root>
    """
    links = YandexSearchAPIClient.extract_yandex_search_links(xml_content)
    assert links == ["https://example.com", "https://test.com"]


def test_extract_yandex_search_links_empty():
    links = YandexSearchAPIClient.extract_yandex_search_links("<root></root>")
    assert links == []



def test_search_and_wait_timeout(client_with_iam, mock_requests):
    mock_post, mock_get = mock_requests

    # Mock search response
    search_response = MagicMock()
    search_response.json.return_value = {"id": "test_op_id"}
    search_response.raise_for_status.return_value = None
    mock_post.return_value = search_response

    # Mock never-done status response
    status_response = MagicMock()
    status_response.json.return_value = {"done": False}
    mock_get.return_value = status_response

    with patch('time.time', side_effect=[0, 301]):  # Simulate timeout
        with pytest.raises(YandexSearchTimeoutError):
            client_with_iam.search_and_wait("test query", max_wait=300)


def test_get_links(client_with_iam, mock_requests):
    mock_post, mock_get = mock_requests

    # Setup mock responses
    search_response = MagicMock()
    search_response.json.return_value = {"id": "test_op_id"}
    search_response.raise_for_status.return_value = None
    mock_post.return_value = search_response

    test_xml = """
    <root>
        <group><doc><url>https://example.com</url></doc></group>
        <group><doc><url>https://test.com</url></doc></group>
    </root>
    """
    status_response = MagicMock()
    status_response.json.return_value = {
        "done": True,
        "response": {"rawData": base64.b64encode(test_xml.encode()).decode('utf-8')}
    }
    mock_get.return_value = status_response

    links = client_with_iam.get_links("test query", n_links=2)
    assert links == ["https://example.com", "https://test.com"]