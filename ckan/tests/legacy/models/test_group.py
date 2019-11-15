# encoding: utf-8

from ckan.tests.legacy import CreateTestData

import ckan.model as model
import pytest


class TestGroup(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create()

    def test_1_basic(self):
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

    def test_2_add_packages(self):
        self.russian_group = model.Group(
            name=u"russian",
            title=u"Russian Group",
            description=u"This is the russian group",
        )

        model.Session.add(self.russian_group)
        anna = model.Package.by_name(u"annakarenina")
        war = model.Package.by_name(u"warandpeace")
        model.Session.add(
            model.Member(
                group=self.russian_group,
                table_id=anna.id,
                table_name="package",
            )
        )
        model.Session.add(
            model.Member(
                group=self.russian_group, table_id=war.id, table_name="package"
            )
        )
        model.repo.commit_and_remove()

        grp = model.Group.by_name(u"russian")
        assert grp.title == u"Russian Group"
        anna = model.Package.by_name(u"annakarenina")
        war = model.Package.by_name(u"warandpeace")
        assert set(grp.packages()) == set((anna, war)), grp.packages()
        assert grp in anna.get_groups()

    def test_3_search(self):
        model.Session.add(
            model.Group(
                name=u"test_org", title=u"Test org", type=u"organization"
            )
        )

        model.repo.commit_and_remove()

        assert self._search_results("random") == set([])
        assert self._search_results("david") == set(["david"])
        assert self._search_results("roger") == set(["roger"])
        assert self._search_results("roger ") == set(["roger"])
        assert self._search_results("David") == set(["david"])
        assert self._search_results("Dave") == set(["david"])
        assert self._search_results("Dave's") == set(["david"])
        assert self._search_results("Dave's books") == set(["david"])
        assert self._search_results("Books") == set(["david", "roger"])
        assert self._search_results("Books", is_org=True) == set([])
        assert self._search_results("Test", is_org=True) == set(["test_org"])

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

    def _search_results(self, query, is_org=False):
        results = model.Group.search_by_name_or_title(query, is_org=is_org)
        return set([group.name for group in results])


name_set_from_dicts = lambda groups: set([group["name"] for group in groups])
name_set_from_group_tuple = lambda tuples: set([t[1] for t in tuples])
name_set_from_groups = lambda groups: set([group.name for group in groups])
names_from_groups = lambda groups: [group.name for group in groups]

group_type = "organization"


class TestHierarchy:
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        CreateTestData.create_group_hierarchy_test_data()

    def test_get_children_groups(self):
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
        groups = model.Group.by_name(
            u"department-of-health"
        ).get_children_group_hierarchy(type=group_type)
        # the first group must be NHS or Food Standards Agency - i.e. on the
        # first level down
        nhs = groups[0]
        assert nhs[1] in ("national-health-service", "food-standards-agency")
        assert model.Group.get(nhs[3]).name == "department-of-health"

    def test_get_children_group_hierarchy__from_top(self):
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
        assert name_set_from_group_tuple(
            model.Group.by_name(
                u"national-health-service"
            ).get_children_group_hierarchy(type=group_type)
        ) == set(("nhs-wirral-ccg", "nhs-southwark-ccg"))
        # i.e. not department-of-health or food-standards-agency

    def test_get_children_group_hierarchy__from_bottom_tier(self):
        assert (
            name_set_from_group_tuple(
                model.Group.by_name(
                    u"nhs-wirral-ccg"
                ).get_children_group_hierarchy(type=group_type)
            )
            == set()
        )

    def test_get_parents__top(self):
        assert (
            names_from_groups(
                model.Group.by_name(u"department-of-health").get_parent_groups(
                    type=group_type
                )
            )
            == []
        )

    def test_get_parents__tier_two(self):
        assert names_from_groups(
            model.Group.by_name(u"national-health-service").get_parent_groups(
                type=group_type
            )
        ) == ["department-of-health"]

    def test_get_parents__tier_three(self):
        assert names_from_groups(
            model.Group.by_name(u"nhs-wirral-ccg").get_parent_groups(
                type=group_type
            )
        ) == ["national-health-service"]

    def test_get_parent_groups_up_hierarchy__from_top(self):
        assert (
            names_from_groups(
                model.Group.by_name(
                    u"department-of-health"
                ).get_parent_group_hierarchy(type=group_type)
            )
            == []
        )

    def test_get_parent_groups_up_hierarchy__from_tier_two(self):
        assert names_from_groups(
            model.Group.by_name(
                u"national-health-service"
            ).get_parent_group_hierarchy(type=group_type)
        ) == ["department-of-health"]

    def test_get_parent_groups_up_hierarchy__from_tier_three(self):
        assert names_from_groups(
            model.Group.by_name(u"nhs-wirral-ccg").get_parent_group_hierarchy(
                type=group_type
            )
        ) == ["department-of-health", "national-health-service"]

    def test_get_top_level_groups(self):
        assert names_from_groups(
            model.Group.by_name(u"nhs-wirral-ccg").get_top_level_groups(
                type=group_type
            )
        ) == ["cabinet-office", "department-of-health"]

    def test_groups_allowed_to_be_its_parent(self):
        groups = model.Group.by_name(
            u"national-health-service"
        ).groups_allowed_to_be_its_parent(type=group_type)
        names = names_from_groups(groups)
        assert "department-of-health" in names
        assert "cabinet-office" in names
        assert "natonal-health-service" not in names
        assert "nhs-wirral-ccg" not in names
