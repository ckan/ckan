# encoding: utf-8

import pytest

import ckan.model as model
from ckan.lib.create_test_data import CreateTestData
from ckan.tests import factories


@pytest.mark.usefixtures
class TestGroup(object):
    def test_basic(self):
        group1 = model.Group(
            name=u"group1",
            title=u"Test Group",
            description=u"This is a test group",
        )
        model.Session.add(group1)
        model.repo.commit_and_remove()
        grp = model.Group.by_name(u"group1")
        assert grp.title == u"Test Group"
        assert grp.description == u"This is a test group"
        assert grp.packages() == []

    def test_add_packages(self):
        self.russian_group = model.Group(
            name=u"russian",
            title=u"Russian Group",
            description=u"This is the russian group",
        )

        model.Session.add(self.russian_group)
        pkg1 = factories.Dataset()
        pkg2 = factories.Dataset()

        model.Session.add(
            model.Member(
                group=self.russian_group,
                table_id=pkg1["id"],
                table_name="package",
            )
        )
        model.Session.add(
            model.Member(
                group=self.russian_group,
                table_id=pkg2["id"],
                table_name="package",
            )
        )
        model.repo.commit_and_remove()

        grp = model.Group.by_name(u"russian")
        assert grp.title == u"Russian Group"
        anna = model.Package.get(pkg1["id"])
        war = model.Package.get(pkg2["id"])
        assert set(grp.packages()) == set((anna, war)), grp.packages()
        assert grp in anna.get_groups()

    def test_search_by_name_or_title_only_returns_active_groups(self):
        active_group = model.Group(name=u"active_group")
        active_group.state = u"active"
        inactive_group = model.Group(name=u"inactive_group")
        inactive_group.state = u"inactive"

        model.Session.add(active_group)
        model.Session.add(inactive_group)
        model.repo.commit_and_remove()

        assert self._search_results("active_group") == set(["active_group"])
        assert self._search_results("inactive_group") == set([])

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


@pytest.mark.usefixtures("clean_db")
class TestHierarchy:
    def test_get_children_groups(self):
        CreateTestData.create_group_hierarchy_test_data()
        res = model.Group.by_name(u"department-of-health").get_children_groups(
            type=group_type
        )
        # check groups
        assert name_set_from_groups(res) == set(
            ("national-health-service", "food-standards-agency")
        )
        # check each group is a Group
        assert isinstance(res[0], model.Group)
        assert res[0].name in (
            "national-health-service",
            "food-standards-agency",
        )
        assert res[0].title in (
            "National Health Service",
            "Food Standards Agency",
        )

    def test_get_children_group_hierarchy__from_top_2(self):
        CreateTestData.create_group_hierarchy_test_data()
        groups = model.Group.by_name(
            u"department-of-health"
        ).get_children_group_hierarchy(type=group_type)
        # the first group must be NHS or Food Standards Agency - i.e. on the
        # first level down
        nhs = groups[0]
        assert nhs[1] in ("national-health-service", "food-standards-agency")
        assert model.Group.get(nhs[3]).name == "department-of-health"

    def test_get_children_group_hierarchy__from_top(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert name_set_from_group_tuple(
            model.Group.by_name(
                u"department-of-health"
            ).get_children_group_hierarchy(type=group_type)
        ) == set(
            (
                "national-health-service",
                "food-standards-agency",
                "nhs-wirral-ccg",
                "nhs-southwark-ccg",
            )
        )
        # i.e. not cabinet-office

    def test_get_children_group_hierarchy__from_tier_two(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert name_set_from_group_tuple(
            model.Group.by_name(
                u"national-health-service"
            ).get_children_group_hierarchy(type=group_type)
        ) == set(("nhs-wirral-ccg", "nhs-southwark-ccg"))
        # i.e. not department-of-health or food-standards-agency

    def test_get_children_group_hierarchy__from_bottom_tier(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert (
            name_set_from_group_tuple(
                model.Group.by_name(
                    u"nhs-wirral-ccg"
                ).get_children_group_hierarchy(type=group_type)
            )
            == set()
        )

    def test_get_parents__top(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert (
            names_from_groups(
                model.Group.by_name(u"department-of-health").get_parent_groups(
                    type=group_type
                )
            )
            == []
        )

    def test_get_parents__tier_two(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert names_from_groups(
            model.Group.by_name(u"national-health-service").get_parent_groups(
                type=group_type
            )
        ) == ["department-of-health"]

    def test_get_parents__tier_three(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert names_from_groups(
            model.Group.by_name(u"nhs-wirral-ccg").get_parent_groups(
                type=group_type
            )
        ) == ["national-health-service"]

    def test_get_parent_groups_up_hierarchy__from_top(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert (
            names_from_groups(
                model.Group.by_name(
                    u"department-of-health"
                ).get_parent_group_hierarchy(type=group_type)
            )
            == []
        )

    def test_get_parent_groups_up_hierarchy__from_tier_two(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert names_from_groups(
            model.Group.by_name(
                u"national-health-service"
            ).get_parent_group_hierarchy(type=group_type)
        ) == ["department-of-health"]

    def test_get_parent_groups_up_hierarchy__from_tier_three(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert names_from_groups(
            model.Group.by_name(u"nhs-wirral-ccg").get_parent_group_hierarchy(
                type=group_type
            )
        ) == ["department-of-health", "national-health-service"]

    def test_get_top_level_groups(self):
        CreateTestData.create_group_hierarchy_test_data()
        assert names_from_groups(
            model.Group.by_name(u"nhs-wirral-ccg").get_top_level_groups(
                type=group_type
            )
        ) == ["cabinet-office", "department-of-health"]

    def test_groups_allowed_to_be_its_parent(self):
        CreateTestData.create_group_hierarchy_test_data()
        groups = model.Group.by_name(
            u"national-health-service"
        ).groups_allowed_to_be_its_parent(type=group_type)
        names = names_from_groups(groups)
        assert "department-of-health" in names
        assert "cabinet-office" in names
        assert "natonal-health-service" not in names
        assert "nhs-wirral-ccg" not in names
