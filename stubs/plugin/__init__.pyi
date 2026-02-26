from typing import Any

class InvenTreePlugin:
    NAME: str
    SLUG: str
    TITLE: str
    DESCRIPTION: str
    VERSION: str
    AUTHOR: str
    MIN_VERSION: str

class _Registry:
    def get_plugin(self, slug: str) -> Any: ...

registry: _Registry
