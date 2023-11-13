from __future__ import annotations

import json
import pytest

from ckan import model
from ckan.cli.generate import generate
from ckan.tests.helpers import CKANCliRunner


@pytest.mark.usefixtures("clean_db")
class TestFakeData:
    def test_generate_using_alias(self, cli: CKANCliRunner):
        """Built-in aliases available out-of-the-box, without additional
        parameters.

        """
        result = cli.invoke(generate, ["fake-data", "organization"])

        assert not result.exit_code, result.output

        org = model.Session.query(model.Group).one()
        assert org.title in result.output

    def test_generate_using_factory_class_argument(self, cli: CKANCliRunner):
        """Factory can be specified via import-string."""
        result = cli.invoke(
            generate, ["fake-data", "ckan.tests.factories:Dataset"]
        )

        assert not result.exit_code, result.output

        dataset = model.Session.query(model.Package).one()
        assert dataset.title in result.output

    def test_generate_using_factory_class_option(self, cli: CKANCliRunner):
        """Factory can be specified via import-string using deprecated option."""
        result = cli.invoke(
            generate,
            ["fake-data", "--factory-class", "ckan.tests.factories:Dataset"],
        )

        assert not result.exit_code, result.output

        dataset = model.Session.query(model.Package).one()
        assert dataset.title in result.output

    def test_generate_using_alias_and_params(self, cli: CKANCliRunner, faker):
        """Alias accepts params for entity fields."""
        name = faker.sentence()
        result = cli.invoke(
            generate, ["fake-data", "resource", f"--name={name}"]
        )

        assert not result.exit_code, result.output
        assert name in result.output

        resource = model.Session.query(model.Resource).one()
        assert resource.name == name

    def test_generate_using_factory_class_and_params(
        self, cli: CKANCliRunner, faker
    ):
        """Factory class accepts params for entity fields."""
        name = faker.name()
        result = cli.invoke(
            generate,
            ["fake-data", "ckan.tests.factories:User", f"--fullname={name}"],
        )

        assert not result.exit_code, result.output
        assert name in result.output

        user = model.Session.query(model.User).filter_by(fullname=name).one()
        assert user.fullname == name

    def test_json_output(self, cli: CKANCliRunner):
        """Command produces valid JSON."""
        result = cli.invoke(generate, ["fake-data", "organization"])
        value = json.loads(result.output)
        assert value

    def test_specify_user_parameter(self, cli: CKANCliRunner, user):
        """Factory accepts username and use it as `context["user"]`."""
        username = user["name"]
        result = cli.invoke(
            generate, [
                "fake-data",
                "dataset",
                f"--user={username}"
            ],
        )

        dataset = json.loads(result.output)
        assert dataset["creator_user_id"] == user["id"]
