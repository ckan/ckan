# -*- coding: utf-8 -*-

import inspect

import ckan.plugins.interfaces as interfaces


def test_no_conflicts_in_method_names():
    ignored = {
        "IDatasetForm",
        "IGroupForm",
        "IOrganizationController",
        "IGroupController",
        "ITagController",
        "IDomainObjectModification",
    }
    classes = dict(
        inspect.getmembers(
            interfaces,
            lambda member: inspect.isclass(member)
            and inspect.getmodule(member) is interfaces,
        )
    )
    methods = {}
    for cls_name, cls in classes.items():
        if cls_name in ignored:
            continue

        for name, _ in inspect.getmembers(cls, inspect.isfunction):
            if name.startswith("_"):
                # ignore private methods
                continue
            assert (
                name not in methods
            ), f"{name} used in {cls_name} and {methods[name]}"
            methods[name] = cls_name
