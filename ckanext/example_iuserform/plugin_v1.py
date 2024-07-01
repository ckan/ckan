from typing import Any, Dict, cast
from ckan.types import Schema, ValidatorFactory
import ckan.plugins as plugins
import ckan.plugins.toolkit as tk


class ExampleIUserFormPlugin1(plugins.SingletonPlugin):
    """An example IUserForm CKAN plugin.

    Adds a custom metadata field to user profiles.
    """

    plugins.implements(plugins.IConfigurer, inherit=False)
    plugins.implements(plugins.IUserForm, inherit=True)

    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        tk.add_template_directory(config, "templates")
        return config

    def _modify_user_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        # Add our custom zip_code metadata field to the schema.
        f = cast(Schema, schema)
        f["zip_code"] = [
            tk.get_validator("ignore_missing"),
            tk.get_converter('convert_to_extras')]
        return f

    def show_user_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        f = cast(Schema, schema)
        f["zip_code"] = [
            tk.get_validator("ignore_missing"),
            tk.get_converter('convert_from_extras')
            ],
        return f

    def create_user_schema(self, schema: Schema) -> Dict[str, Any]:
        schema = super(ExampleIUserFormPlugin1, self).create_user_schema(
            schema
        )
        schema = self._modify_user_schema(schema)
        return schema

    def update_user_schema(self, schema: Schema) -> Dict[str, Any]:
        schema = super(ExampleIUserFormPlugin1, self).update_user_schema(
            schema
        )
        schema = self._modify_user_schema(schema)
        return schema
