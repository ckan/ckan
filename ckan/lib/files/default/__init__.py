import contextlib
from .fs import FsStorage, PublicFsStorage

with contextlib.suppress(ImportError):
    from .libcloud import LibCloudStorage

with contextlib.suppress(ImportError):
    from .opendal import OpenDalStorage

from .null import NullStorage

__all__ = [
    "NullStorage",
    "FsStorage",
    "PublicFsStorage",
    "LibCloudStorage",
    "OpenDalStorage",
]
