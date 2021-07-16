# encoding: utf-8

from __future__ import print_function
import pytest
import ckan.model as model


class TestResource:
    pkgname = "resourcetest"
    urls = ["http://somewhere.com/", "http://elsewhere.com/"]
    format = "csv"
    description = "Important part."
    hash = "abc123"
    alt_url = "http://alturl"
    size = 200
    label = "labeltest"
    sort_order = "1"

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        assert not model.Package.by_name(self.pkgname)
        assert model.Session.query(model.Resource).count() == 0
        pkg = model.Package(name=self.pkgname)
        model.Session.add(pkg)
        for url in self.urls:
            pr = model.Resource(
                url=url,
                format=self.format,
                description=self.description,
                hash=self.hash,
                alt_url=self.alt_url,
                extras={"size": self.size},
                package_id=pkg.id,
            )
            pkg.resources_all.append(pr)
        pr = model.Resource(
            url="no_extra",
            format=self.format,
            description=self.description,
            hash=self.hash,
            package_id=pkg.id,
        )
        pkg.resources_all.append(pr)
        model.repo.commit_and_remove()

    def teardown(self):
        model.repo.rebuild_db()

    def test_01_create_package_resources(self):

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources_all) == 3, pkg.resources

        resource_0 = pkg.resources_all[0]

        assert resource_0.url == self.urls[0], resource_0
        assert resource_0.description == self.description, resource_0
        assert resource_0.hash == self.hash, resource_0
        assert resource_0.position == 0, resource_0.position
        assert resource_0.alt_url == self.alt_url, resource_0.alt_url
        assert resource_0.extras["size"] == self.size

        generated_dict_resource = resource_0.as_dict()
        assert (
            generated_dict_resource["alt_url"] == "http://alturl"
        ), generated_dict_resource["alt_url"]
        assert generated_dict_resource["size"] == 200

        ## check to see if extra descriptor deletes properly
        del resource_0.extras["size"]
        assert resource_0.extras == {
            "alt_url": "http://alturl"
        }, pkg.resources[0].extras

        del resource_0.alt_url
        assert resource_0.extras == {}, pkg.resources[0].extras
        assert resource_0.alt_url is None

        resource_0.alt_url = "weeee"
        assert resource_0.extras == {"alt_url": "weeee"}, resource_0.extras

        model.Session.add(resource_0)

        model.repo.commit_and_remove()
        pkg = model.Package.by_name(self.pkgname)

        assert resource_0.extras == {"alt_url": "weeee"}, resource_0.extras
        assert resource_0.alt_url == "weeee", resource_0.alt_url

        pkg = model.Package.by_name(self.pkgname)

        assert pkg.resources[2].extras == {}, pkg.resources[2].extras

    def test_02_delete_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        res = pkg.resources[0]
        assert len(pkg.resources) == 3, pkg.resources
        res.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 2, pkg.resources
        assert len(pkg.resources_all) == 3, pkg.resources_all

    def test_03_reorder_resources(self):
        pkg = model.Package.by_name(self.pkgname)

        res0 = pkg.resources_all[0]
        del pkg.resources_all[0]
        pkg.resources_all.append(res0)
        # this assert will fail
        # assert pkg.resources[1].position == 1
        # Why? According to docs for ordering list it does not reorder appended
        # elements by default (see
        # http://www.sqlalchemy.org/trac/browser/lib/sqlalchemy/ext/orderinglist.py#L197)
        # so we have to call reorder directly in supported versions
        # of sqlalchemy and set position to None in older ones.
        pkg.resources_all.reorder()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources_all) == 3, len(pkg.resources)
        lastres = pkg.resources[2]
        assert lastres.position == 2, lastres
        print(lastres)
        assert lastres.url == self.urls[0], (self.urls, lastres.url)

    def test_04_insert_resource(self):
        pkg = model.Package.by_name(self.pkgname)
        newurl = "http://xxxxxxxxxxxxxxx"

        resource = model.Resource(url=newurl)
        pkg.resources_all.insert(0, resource)
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.resources) == 4, pkg.resources
        assert pkg.resources_all[1].url == self.urls[0]

    def test_05_delete_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource)
        active_resources = model.Session.query(model.Resource).filter_by(
            state=model.State.ACTIVE
        )
        assert all_resources.count() == 3, all_resources.all()
        assert active_resources.count() == 3, active_resources.count()
        pkg.delete()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        # OK for resources remain active
        assert all_resources.count() == 3, all_resources.all()
        assert active_resources.count() == 3, active_resources.count()

    def test_07_purge_package(self):
        pkg = model.Package.by_name(self.pkgname)
        all_resources = model.Session.query(model.Resource).all()
        assert len(all_resources) == 3, pkg.resources
        pkg.purge()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(self.pkgname)
        all_resources = (
            model.Session.query(model.Resource)
            .filter_by(state=model.State.ACTIVE)
            .all()
        )
        assert len(all_resources) == 0, pkg.resources
