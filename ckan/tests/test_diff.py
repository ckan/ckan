import ckan.model as model
import ckan.lib.diff as diff
from ckan.tests import *

# TODO Get this working
class _TestDiffPackage(TestController):

    @classmethod
    def setup_class(self):
        model.Session.remove()

        # create test package
        rev = model.repo.new_revision()
        pkg = model.Package(name=u'difftest')
        pkg.title = u'Test title'
        pkg.url = u'editpkgurl.com'
        pkg.add_resource(u'editpkgurl2.com')
        pkg.notes= u'this\nis\neditpkg'
        pkg.version = u'2.2'
        pkg.maintainer = u'Bob'
        pkg.maintainer_email = u'bob@bob.net'
        pkg.author = u'Gary'
        pkg.author_email = u'gary@gary.net'
        def get_tag(name):
            tag = model.Tag.by_name(name)
            if not tag:
                tag = model.Tag(name=name)
            return tag
        pkg.tags = [get_tag(u'one'), get_tag(u'two')]
        pkg.state = model.State.DELETED
        tags_txt = ' '.join([tag.name for tag in pkg.tags])
        pkg.license = model.License.by_name(u'OKD Compliant::Other')
        extras = {'key1':'value1', 'key2':'value2', 'key3':'value3'}
        for key, value in extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(u'difftest')
        assert len(self.pkg.all_revisions) == 1
        self.old_pkg_rev = self.pkg.all_revisions[0]
        self.old_rev = self.old_pkg_rev.revision

        # revise test package
        rev = model.repo.new_revision()
        pkg = model.Package.by_name(u'difftest')
        pkg.title = u'Test CHANGED title'
        pkg.url = u'editpkgurl.com CHANGED'
        pkg.resources = []
        pkg.add_resource(u'editpkgurl2.com CHANGED')
        pkg.notes = u'this\nis\neditpkg CHANGED'
        pkg.version = u'2.2 CHANGED'
        pkg.maintainer = u'Bob2'
        pkg.maintainer_email = u'bob2@bob.net'
        pkg.author = u'Gary2'
        pkg.author_email = u'gary2@gary.net'
        pkg.tags = [get_tag(u'one'), get_tag(u'three')]
        for package_tag in pkg.package_tags:
            if package_tag.tag.name ==u'two':
                package_tag.delete()
        pkg.state = model.State.ACTIVE
        pkg.license = model.License.by_name(u'OKD Compliant::UK Click Use PSI')
        extras = {'key1':'value1', 'key2':'value2-changed', 'key3':None, 'key4':'all-new'}
        for key, value in extras.items():
            pkg.extras[unicode(key)] = unicode(value)
        model.repo.commit_and_remove()

        self.pkg = model.Package.by_name(u'difftest')
        self.pkg_revs = self.pkg.all_revisions
        assert len(self.pkg_revs) == 2
        self.new_pkg_rev = self.pkg_revs[0] if self.pkg_revs[1].id == self.old_pkg_rev.id else self.pkg_revs[1]
        self.new_rev = self.new_pkg_rev.revision
        self.differ = model.repo.diff_object

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_1_package(self):
        assert len(self.pkg_revs) == 2, self.revs
        out = self.differ(self.pkg, obj_rev1=self.old_pkg_rev, obj_rev2=self.new_pkg_rev)
        assert out
        reqd_keys = ['maintainer', 'license', 'author', 'url', 'notes', 'title', 'resources', 'maintainer_email', 'author_email', 'state', 'version']
        out_keys = out.keys()
        print out
        for reqd_key in reqd_keys:
            assert reqd_key in out_keys, '%s %s' % (out_keys, reqd_key)
        assert out['title'] == u'- Test title\n+ Test CHANGED title', out['title']
        assert out['url'].startswith(u'- editpkgurl.com\n+ editpkgurl.com CHANGED'), out['url']
        assert out['resources'].startswith(u'- editpkgurl2.com\n+ editpkgurl2.com CHANGED'), out['resources']
        assert out['notes'] == u'  this\n  is\n- editpkg\n+ editpkg CHANGED', out['notes']
        assert out['version'] == u'- 2.2\n+ 2.2 CHANGED', out['version']
        assert not out.has_key('tags')
        assert out['state'] == u'- deleted\n+ active', out['state']
        assert out['license'] == u'- OKD Compliant::Other\n+ OKD Compliant::UK Click Use PSI', out['license']
        assert not out.has_key('extras')

    def _check_tags_in(self, tag_list, tagname_list):
        assert len(tag_list) == len(tagname_list), tag_list
        for tagname in tagname_list:
            tag = model.Tag.by_name(tagname)
            assert tag in tag_list, '%s not in %r' % (tagname, tag_list)

    def test_2_tags(self):
        def tag(name):
            return model.Tag.by_name(name)

        old_tags = self.old_rev.package_tags[self.pkg]
        new_tags = self.new_rev.package_tags[self.pkg]

        self._check_tags_in(old_tags, (u'one', u'two'))
        self._check_tags_in(new_tags, (u'one', u'three'))

        

