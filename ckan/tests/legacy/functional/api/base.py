# encoding: utf-8

from six.moves.urllib.parse import quote

from ckan.tests.legacy import TestController as ControllerTestCase, CreateTestData
from ckan.common import json


ACCESS_DENIED = [403]


class ApiTestCase(object):

    STATUS_200_OK = 200
    STATUS_201_CREATED = 201
    STATUS_400_BAD_REQUEST = 400
    STATUS_403_ACCESS_DENIED = 403
    STATUS_404_NOT_FOUND = 404
    STATUS_409_CONFLICT = 409

    send_authorization_header = True
    extra_environ = {}

    api_version = None

    ref_package_by = ""
    ref_group_by = ""

    def get(self, offset, status=200):
        response = self.app.get(
            offset, status=status, extra_environ=self.get_extra_environ()
        )
        return response

    def post(self, offset, data, status=200, *args, **kwds):
        params = "%s=1" % quote(self.dumps(data))
        if "extra_environ" in kwds:
            self.extra_environ = kwds["extra_environ"]
        response = self.app.post(
            offset,
            params=params,
            status=status,
            extra_environ=self.get_extra_environ(),
        )
        return response

    def app_delete(self, offset, status=200, *args, **kwds):
        response = self.app.delete(
            offset, status=status, extra_environ=self.get_extra_environ()
        )
        return response

    def get_extra_environ(self):
        extra_environ = {}
        for (key, value) in self.extra_environ.items():
            if key == "Authorization":
                if self.send_authorization_header == True:
                    extra_environ[key] = value
            else:
                extra_environ[key] = value
        return extra_environ

    @classmethod
    def offset(self, path):
        """
        Returns the full path to the resource identified in path.

        Performs necessary url-encodings, ie:

         - encodes unicode to utf8
         - urlencodes the resulting byte array

        This process is described in [1], and has also been confirmed by
        inspecting what a browser does.

        [1] http://www.w3.org/International/articles/idn-and-iri/
        """
        assert self.api_version != None, "API version is missing."
        base = "/api"
        if self.api_version:
            base += "/%s" % self.api_version
        utf8_encoded = (u"%s%s" % (base, path)).encode("utf8")
        url_encoded = quote(utf8_encoded)
        return url_encoded

    def assert_msg_represents_anna(self, msg):
        assert "annakarenina" in msg, msg
        data = self.loads(msg)
        assert data["name"] == "annakarenina"
        assert data["license_id"] == "other-open"
        assert '"license_id": "other-open"' in msg, str(msg)
        assert "russian" in msg, msg
        assert "tolstoy" in msg, msg
        assert '"extras": {' in msg, msg
        assert '"genre": "romantic novel"' in msg, msg
        assert '"original media": "book"' in msg, msg
        assert "datahub.io/download" in msg, msg
        assert '"plain text"' in msg, msg
        assert '"Index of the novel"' in msg, msg
        assert '"id": "%s"' % self.anna.id in msg, msg
        expected = '"groups": ['
        assert expected in msg, (expected, msg)
        expected = self.group_ref_from_name("roger")
        assert expected in msg, (expected, msg)
        expected = self.group_ref_from_name("david")
        assert expected in msg, (expected, msg)

        # Todo: What is the deal with ckan_url? And should this use IDs rather than names?
        assert "ckan_url" in msg
        assert (
            '"ckan_url": "http://test.ckan.net/dataset/annakarenina"' in msg
        ), msg

        assert "tags" in data, "Expected a tags list in json payload"
        assert self.russian.name in data["tags"], data["tags"]
        assert self.tolstoy.name in data["tags"], data["tags"]
        assert self.flexible_tag.name in data["tags"], data["tags"]

    def assert_msg_represents_roger(self, msg):
        assert "roger" in msg, msg
        data = self.loads(msg)
        keys = set(data.keys())
        expected_keys = set(
            [
                "id",
                "name",
                "title",
                "description",
                "created",
                "state",
                "packages",
            ]
        )
        missing_keys = expected_keys - keys
        assert not missing_keys, missing_keys
        assert data["name"] == "roger"
        assert data["title"] == "Roger's books"
        assert data["description"] == "Roger likes these books."
        assert data["state"] == "active"
        assert data["packages"] == [self._ref_package(self.anna)]

    def assert_msg_represents_russian(self, msg):
        data = self.loads(msg)
        pkgs = set(data)
        expected_pkgs = set(
            [
                self.package_ref_from_name("annakarenina"),
                self.package_ref_from_name("warandpeace"),
            ]
        )
        differences = expected_pkgs ^ pkgs
        assert not differences, "%r != %r" % (pkgs, expected_pkgs)

    def assert_msg_represents_flexible_tag(self, msg):
        """
        Asserts the correct packages are associated with the flexible tag.

        Namely, 'annakarenina' and 'warandpeace'.
        """
        data = self.loads(msg)
        pkgs = set(data)
        expected_pkgs = set(
            [
                self.package_ref_from_name("annakarenina"),
                self.package_ref_from_name("warandpeace"),
            ]
        )
        differences = expected_pkgs ^ pkgs
        assert not differences, "%r != %r" % (pkgs, expected_pkgs)

    def data_from_res(self, res):
        return self.loads(res.body)

    def package_ref_from_name(self, package_name):
        package = self.get_package_by_name(package_name)
        if package is None:
            return package_name
        else:
            return self.ref_package(package)

    def package_id_from_ref(self, package_name):
        package = self.get_package_by_name(package_name)
        if package is None:
            return package_name
        else:
            return self.ref_package(package)

    def ref_package(self, package):
        assert self.ref_package_by in ["id", "name"]
        return getattr(package, self.ref_package_by)

    def get_expected_api_version(self):
        return self.api_version

    def dumps(self, data):
        return json.dumps(data)

    def loads(self, chars):
        try:
            return json.loads(chars)
        except ValueError as inst:
            raise Exception("Couldn't loads string '%s': %s" % (chars, inst))

    def assert_json_response(self, res, expected_in_body=None):
        content_type = res.headers.get("Content-Type")
        assert "application/json" in content_type, content_type
        res_json = self.loads(res.body)
        if expected_in_body:
            assert expected_in_body in res_json or expected_in_body in str(
                res_json
            ), (
                "Expected to find %r in JSON response %r"
                % (expected_in_body, res_json)
            )


class Api3TestCase(ApiTestCase):

    api_version = 3
    ref_package_by = "name"
    ref_group_by = "name"
    ref_tag_by = "name"

    def assert_msg_represents_anna(self, msg):
        super(ApiTestCase, self).assert_msg_represents_anna(msg)
        assert "download_url" not in msg, msg
