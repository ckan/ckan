import uuid

__all__ = ["make_uuid"]


def make_uuid() -> str:
    return str(uuid.uuid4())
