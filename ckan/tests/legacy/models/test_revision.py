# encoding: utf-8

import datetime

import pytest

import ckan.model as model

# NB Lots of revision tests are part of vdm. No need to repeat those here.


class TestRevision:
    @pytest.fixture
    def rev(self):
        # Create a test package
        rev = model.repo.new_revision()
        rev.author = "Tester"
        rev.timestamp = datetime.datetime(2020, 1, 1)
        rev.approved_timestamp = datetime.datetime(2020, 1, 2)
        rev.message = "Test message"
        pkg = model.Package(name="testpkg")
        model.Session.add(pkg)
        model.Session.commit()
        model.Session.remove()

        revs = (
            model.Session.query(model.Revision)
            .order_by(model.Revision.timestamp.desc())
            .all()
        )
        return revs[0]  # newest

    def test_revision_as_dict(self, rev):
        rev_dict = model.revision_as_dict(
            rev,
            include_packages=True,
            include_groups=True,
            ref_package_by="name",
        )

        assert rev_dict["id"] == rev.id
        assert rev_dict["author"] == rev.author
        assert rev_dict["timestamp"] == "2020-01-01T00:00:00"
        assert rev_dict["approved_timestamp"] == "2020-01-02T00:00:00"
        assert rev_dict["message"] == rev.message
        assert rev_dict["packages"] == [u"testpkg"]
