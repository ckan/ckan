# -*- coding: utf-8 -*-

from flask import Blueprint

__all__ = [u"blanket"]

blanket = Blueprint(u"blanket", __name__)


def dream():
    pass


blanket.add_url_rule(u"/sleep", view_func=dream)


def get_blueprints():
    return [blanket]
