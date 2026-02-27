# encoding: utf-8
from __future__ import annotations

from ckan.plugins.interfaces import Interface
from typing import Any


class IStats(Interface):
    """
    The IStats interface allows plugin authors to modify stats

    The before_submit function, when implemented
    """

    def after_stats(self, stats: dict[str, Any]) -> dict[str, Any]:
        """
        Called after stats are generated in the stats.index blueprint

        :param stats: a dictionary of stats
        :type stats: dict
        """
        return stats
