import pytest

from ckan import model
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
class TestVocabulary:
    ...
