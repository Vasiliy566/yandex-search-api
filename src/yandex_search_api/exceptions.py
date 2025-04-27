class YandexSearchAPIError(Exception):
    """Base exception for Yandex Search API errors"""
    pass

class YandexSearchTimeoutError(YandexSearchAPIError):
    """Exception raised when waiting for results times out"""
    pass

class YandexAuthError(YandexSearchAPIError):
    """Exception raised for authentication errors"""
    pass
