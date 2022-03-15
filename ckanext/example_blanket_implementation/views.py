# -*- coding: utf-8 -*-

from flask import Blueprint

__all__ = [u"blanket"]

blanket = Blueprint(u"blanket", __name__)


@blanket.route("/sleep")
def dream():
    return ""


def get_blueprints():
    return [blanket]
