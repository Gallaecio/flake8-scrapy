from typing import Any


# https://github.com/scrapy/scrapy/blob/2.13.2/scrapy/settings/__init__.py#L152-L180
def getbool(value: Any) -> bool:
    try:
        return bool(int(value))
    except ValueError:
        pass
    if value in ("True", "true"):
        return True
    if value in ("False", "false"):
        return False
    raise ValueError
