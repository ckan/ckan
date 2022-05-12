# encoding: utf-8

import pytest

import ckan.model as model
from ckan.tests import factories


@pytest.mark.usefixtures("non_clean_db")
class TestGroup(object):
    def test_basic(self):
        group = model.Group(
            name=factories.Group.stub().name,
            title=u"Test Group",
            description=u"This is a test group",
        )
        model.Session.add(group)
        model.repo.commit_and_remove()
        grp = model.Group.by_name(group.name)
        assert grp.title == u"Test Group"
        assert grp.description == u"This is a test group"
        assert grp.packages() == []

    def test_add_packages(self):
        group = model.Group(
            name=factories.Group.stub().name,
            title=u"Russian Group",
            description=u"This is the russian group",
        )

        model.Session.add(group)
        pkg1 = factories.Dataset()
        pkg2 = factories.Dataset()

        model.Session.add(
            model.Member(
                group=group,
                table_id=pkg1["id"],
                table_name="package",
            )
        )
        model.Session.add(
            model.Member(
                group=group,
                table_id=pkg2["id"],
                table_name="package",
            )
        )
        model.repo.commit_and_remove()

        grp = model.Group.by_name(group.name)
        assert grp.title == u"Russian Group"
        anna = model.Package.get(pkg1["id"])
        war = model.Package.get(pkg2["id"])
        assert set(grp.packages()) == set((anna, war)), grp.packages()
        assert grp in anna.get_groups()

    def test_search_by_name_or_title_only_returns_active_groups(self):
        active_group = model.Group(name=factories.Group.stub().name)
        active_group.state = u"active"
        inactive_group = model.Group(name=factories.Group.stub().name)
        inactive_group.state = u"inactive"

        model.Session.add(active_group)
        model.Session.add(inactive_group)
        model.repo.commit_and_remove()

        assert self._search_results(active_group.name) == set(
            [active_group.name]
        )
        assert self._search_results(inactive_group.name) == set([])

    def _search_results(self, query):
        results = model.Group.search_by_name_or_title(query, is_org=False)
        return set([group.name for group in results])


def name_set_from_dicts(groups):
    return set([group["name"] for group in groups])


def name_set_from_group_tuple(tuples):
    return set([t[1] for t in tuples])


def name_set_from_groups(groups):
    return set([group.name for group in groups])


def names_from_groups(groups):
    return [group.name for group in groups]


group_type = "organization"


@pytest.fixture()
def hierarchy(non_clean_db):
    left = factories.Organization.model()
    left_leaf = factories.Organization.model(parent_id=left.id)
    left_branch = factories.Organization.model(parent_id=left.id)
    child1 = factories.Organization.model(parent_id=left_branch.id)
    child2 = factories.Organization.model(parent_id=left_branch.id)
    right = factories.Organization.model()

    model.Session.add(
        model.Member(
            group=left_leaf,
            table_id=left.id,
            table_name="group",
            capacity="parent",
        )
    )
    model.Session.add(
        model.Member(
            group=left_branch,
            table_id=left.id,
            table_name="group",
            capacity="parent",
        )
    )
    model.Session.add(
        model.Member(
            group=child1,
            table_id=left_branch.id,
            table_name="group",
            capacity="parent",
        )
    )
    model.Session.add(
        model.Member(
            group=child2,
            table_id=left_branch.id,
            table_name="group",
            capacity="parent",
        )
    )
    model.Session.commit()

    return {
        "top_single": right,
        "top_branch": left,
        "tree": {
            "mid_single": left_leaf,
            "mid_branch": left_branch,
            "tree": [
                child1,
                child2,
            ],
        },
    }


class TestHierarchy:
    def test_get_children_groups(self, hierarchy):
        res = hierarchy["top_branch"].get_children_groups(type=group_type)
        # check groups
        assert name_set_from_groups(res) == set(
            (
                hierarchy["tree"]["mid_branch"].name,
                hierarchy["tree"]["mid_single"].name,
            )
        )
        # check each group is a Group
        assert isinstance(res[0], model.Group)
        assert res[0].name in (
            hierarchy["tree"]["mid_branch"].name,
            hierarchy["tree"]["mid_single"].name,
        )
        assert res[0].title in (
            hierarchy["tree"]["mid_branch"].title,
            hierarchy["tree"]["mid_single"].title,
        )

    def test_get_children_group_hierarchy__from_top_2(self, hierarchy):
        groups = hierarchy["top_branch"].get_children_group_hierarchy(
            type=group_type
        )
        # the first group must be NHS or Food Standards Agency - i.e. on the
        # first level down
        nhs = groups[0]
        assert nhs[1] in (
            hierarchy["tree"]["mid_branch"].name,
            hierarchy["tree"]["mid_single"].name,
        )
        assert model.Group.get(nhs[3]).name == hierarchy["top_branch"].name

    def test_get_children_group_hierarchy__from_top(self, hierarchy):
        assert name_set_from_group_tuple(
            hierarchy["top_branch"].get_children_group_hierarchy(
                type=group_type
            )
        ) == set(
            (
                hierarchy["tree"]["mid_branch"].name,
                hierarchy["tree"]["mid_single"].name,
                hierarchy["tree"]["tree"][0].name,
                hierarchy["tree"]["tree"][1].name,
            )
        )
        # i.e. not top_single

    def test_get_children_group_hierarchy__from_tier_two(self, hierarchy):
        assert name_set_from_group_tuple(
            hierarchy["tree"]["mid_branch"].get_children_group_hierarchy(
                type=group_type
            )
        ) == set(
            (
                hierarchy["tree"]["tree"][0].name,
                hierarchy["tree"]["tree"][1].name,
            )
        )
        # i.e. not top_branch or mid_single

    def test_get_children_group_hierarchy__from_bottom_tier(self, hierarchy):
        assert (
            name_set_from_group_tuple(
                hierarchy["tree"]["tree"][0].get_children_group_hierarchy(
                    type=group_type
                )
            )
            == set()
        )

    def test_get_parents__top(self, hierarchy):
        assert (
            names_from_groups(
                hierarchy["top_branch"].get_parent_groups(type=group_type)
            )
            == []
        )

    def test_get_parents__tier_two(self, hierarchy):
        assert names_from_groups(
            hierarchy["tree"]["mid_branch"].get_parent_groups(type=group_type)
        ) == [hierarchy["top_branch"].name]

    def test_get_parents__tier_three(self, hierarchy):
        assert names_from_groups(
            hierarchy["tree"]["tree"][0].get_parent_groups(type=group_type)
        ) == [hierarchy["tree"]["mid_branch"].name]

    def test_get_parent_groups_up_hierarchy__from_top(self, hierarchy):
        assert (
            names_from_groups(
                hierarchy["top_branch"].get_parent_group_hierarchy(
                    type=group_type
                )
            )
            == []
        )

    def test_get_parent_groups_up_hierarchy__from_tier_two(self, hierarchy):
        assert names_from_groups(
            hierarchy["tree"]["mid_branch"].get_parent_group_hierarchy(
                type=group_type
            )
        ) == [hierarchy["top_branch"].name]

    def test_get_parent_groups_up_hierarchy__from_tier_three(self, hierarchy):
        assert names_from_groups(
            hierarchy["tree"]["tree"][0].get_parent_group_hierarchy(
                type=group_type
            )
        ) == [
            hierarchy["top_branch"].name,
            hierarchy["tree"]["mid_branch"].name,
        ]

    def test_get_top_level_groups(self, hierarchy):
        groups = names_from_groups(
            hierarchy["tree"]["tree"][0].get_top_level_groups(type=group_type)
        )
        assert hierarchy["top_single"].name in groups
        assert hierarchy["top_branch"].name in groups

    def test_groups_allowed_to_be_its_parent(self, hierarchy):
        groups = hierarchy["tree"][
            "mid_branch"
        ].groups_allowed_to_be_its_parent(type=group_type)
        names = names_from_groups(groups)
        assert hierarchy["top_branch"].name in names
        assert hierarchy["top_single"].name in names
        assert hierarchy["tree"]["tree"][0].name not in names
        assert hierarchy["tree"]["tree"][1].name not in names
