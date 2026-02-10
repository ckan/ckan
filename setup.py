# encoding: utf-8

import os
from setuptools import setup

# Avoid problem releasing to pypi from vagrant
if os.environ.get("USER", "") == "vagrant":
    del os.link

extras_require = {}
_extras_groups = [
    ("requirements", "requirements.txt"),
    ("dev", "dev-requirements.txt"),
]

HERE = os.path.dirname(__file__)
for group, filepath in _extras_groups:
    with open(os.path.join(HERE, filepath), "r") as f:
        extras_require[group] = f.readlines()

setup(
    message_extractors={
        "ckan": [
            ("**.py", "python", None),
            ("**.js", "javascript", None),
            ("templates/**.html", "ckan", None),
            ("templates/**.txt", "ckan", None),
            ("public/**", "ignore", None),
        ],
        "ckanext": [
            ("**.py", "python", None),
            ("**.js", "javascript", None),
            ("**.html", "ckan", None),
            ("multilingual/solr/*.txt", "ignore", None),
        ],
    },
    extras_require=extras_require,
)
