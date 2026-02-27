# -*- coding: utf-8 -*-

"""Tests for the ``ckan clean activities`` CLI command."""

import pytest

import ckan.model as model
from ckan.cli.cli import ckan
from ckan.tests import factories

from ckanext.activity.model import Activity
from ckanext.activity.tests.conftest import ActivityFactory


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

    def test_clean_activities_quiet_no_activities(self, cli):
        """With -q and no matching activities, shows no-activities message."""
        result = cli.invoke(
            ckan,
            ["clean", "activities", "--offset_days", "30", "--quiet"],
        )
        assert result.exit_code == 0
        assert "No activities found" in result.output

    def test_clean_activities_validation_error_without_params(self, cli):
        """Without date range or offset_days, validation error is shown."""
        result = cli.invoke(ckan, ["clean", "activities", "--quiet"])
        assert result.exit_code != 0 or "Validation" in result.output
        assert "Validation" in result.output or "criteria" in result.output

    @pytest.mark.freeze_time
    def test_clean_activities_quiet_deletes_activities(self, cli, freezer):
        """With -q and offset_days, matching activities are deleted."""
        freezer.move_to("2023-01-01 12:00:00")
        sysadmin = factories.Sysadmin()
        dataset = factories.Dataset()
        ActivityFactory(
            activity_type="changed package",
            object_id=dataset["id"],
            user_id=sysadmin["id"],
        )
        model.Session.commit()
        initial_count = model.Session.query(Activity).count()
        assert initial_count >= 1

        freezer.move_to("2023-02-15 12:00:00")
        result = cli.invoke(
            ckan,
            ["clean", "activities", "--offset_days", "60", "--quiet"],
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output or "rows" in result.output
        assert model.Session.query(Activity).count() == 0

    @pytest.mark.freeze_time
    def test_clean_activities_quiet_with_date_range(self, cli, freezer):
        """With -q and start_date/end_date, activities in range are deleted."""
        freezer.move_to("2023-01-15 12:00:00")
        sysadmin = factories.Sysadmin()
        dataset = factories.Dataset()
        ActivityFactory(
            activity_type="changed package",
            object_id=dataset["id"],
            user_id=sysadmin["id"],
        )
        model.Session.commit()
        assert model.Session.query(Activity).count() >= 1

        result = cli.invoke(
            ckan,
            [
                "clean", "activities",
                "--start_date", "2023-01-01",
                "--end_date", "2023-01-31",
                "--quiet",
            ],
        )
        assert result.exit_code == 0
        assert model.Session.query(Activity).count() == 0
