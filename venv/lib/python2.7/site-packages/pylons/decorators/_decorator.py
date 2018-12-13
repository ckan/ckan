"""Provides the decorator module for pylons.decorator backwards compatibility.

pylons.decorator can't import the decorator module itself due to relative
imports name clashing.
"""
from decorator import *
