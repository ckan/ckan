import contextlib

from .fs import FsStorage, PublicFsStorage

with contextlib.suppress(ImportError):
    from .libcloud import LibCloudStorage

with contextlib.suppress(ImportError):
    from .opendal import OpenDalStorage

with contextlib.suppress(ImportError):
    from .azure_blob import AzureBlobStorage

with contextlib.suppress(ImportError):
    from .gcs import GoogleCloudStorage

with contextlib.suppress(ImportError):
    from .s3 import S3Storage


from .memory import MemoryStorage
from .null import NullStorage

__all__ = [
    "AzureBlobStorage",
    "FsStorage",
    "GoogleCloudStorage",
    "LibCloudStorage",
    "MemoryStorage",
    "NullStorage",
    "OpenDalStorage",
    "PublicFsStorage",
    "S3Storage",
]
