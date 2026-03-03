# -*- coding: utf-8 -*-

"""Tests for the ``ckan clean activities`` CLI command.
Delete behaviour (by offset_days, date range, no activities, etc.) is covered
in logic/test_action.py (TestActivityDeleteByDateRangeOrOffset and related).
These tests only cover the unique CLI functionality: command registration
and making sure invalid params do not succeed.
"""

import pytest

from ckan.cli.cli import ckan


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestCleanActivitiesCli:
    """Tests for ``ckan clean activities``."""

    def test_clean_activities_help(self, cli):
        """Help text is shown for clean activities command."""
        result = cli.invoke(ckan, ["clean", "activities", "--help"])
        assert result.exit_code == 0
        assert "Deletes activities" in result.output
        assert "--offset_days" in result.output
        assert "--start_date" in result.output
        assert "--end_date" in result.output
        assert "--quiet" in result.output or "-q" in result.output

    def test_clean_activities_fails_without_params(self, cli):
        """Without date range or offset_days, the command does not succeed."""
        result = cli.invoke(ckan, ["clean", "activities", "--quiet"])
        # Either non-zero exit (e.g. action not found in CLI context) or
        # validation error message
        assert result.exit_code != 0 or "Validation" in result.output or "criteria" in result.output
