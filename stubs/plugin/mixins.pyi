from typing import Any

class SettingsMixin:
    def get_setting(self, key: str) -> Any: ...

class UrlsMixin:
    def setup_urls(self) -> list[Any]: ...
