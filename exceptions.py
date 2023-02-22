class InvalidApi(Exception):
    """Ошибка ответа API."""
    pass


class EmptyList(Exception):
    """Список пустой."""
    pass


class InvalidResponse(Exception):
    """Ошибка запроса."""
    pass
