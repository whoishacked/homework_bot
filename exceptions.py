class HomeWorkStatusesException(Exception):
    """Исключение, если статус домашней работы отсутсвует в словаре
    вердиктов"""
    pass


class APIStatusesException(Exception):
    """Исключение, если код ответа от сервера API != 200"""
    pass


class HomeWorkTypeError(Exception):
    """Исключение, если от API в качестве homewroks получили не словарь"""
    pass


class TokenError(Exception):
    """Исключение, если возникли проблемы с токенами"""
    pass


class JsonError(Exception):
    """Исключение для ошибок при соединении с енд-поинт"""
    pass


class APIAnswerKeyError(Exception):
    """Исключение для ошибок при использовании несуществующих ключей"""
    pass
