# -*- coding: utf-8 -*-

import click

__all__ = [u"blanket"]


def blanket_helper():
    pass


def _hidden_helper():
    pass


@click.group()
def blanket():
    pass


@blanket.command()
def duvet():
    pass
