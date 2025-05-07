# Local testing

This is a set of scripts that replicate the contents of `/.github/workflows/pytest.yml`, enabling testing on the local machine with the same setup as GitHub Actions. It requires docker with the compose plugin to be installed and on the path, as well as the `sh` shell. It should work out of the box on linux/mac, Windows is unknown.

NOTE: This is not intended to be a pattern for running anything other than tests. This is not a deployment template.


## To Run.

```
$ cd test-infrastructure
test-infrastructure$ ./setup.sh
[[
* docker composee downloads images and starts the stack
* System level dependencies (psql) are installed
* Python dependencies are installed, ckan is installed in edit mode
* Database creation and database initialization are done
]]
test-infrastructure$ ./execute.sh
$ ./execute.sh
2022-09-22 14:42:28,959 INFO  [ckan.cli] Using configuration file /usr/src/test-core-ci.ini
2022-09-22 14:42:28,960 INFO  [ckan.config.environment] Loading static files from public
2022-09-22 14:42:29,371 WARNI [ckan.common] Option ckan.plugins is not declared
2022-09-22 14:42:29,618 INFO  [ckan.config.environment] Loading templates from /usr/src/ckan/templates
2022-09-22 14:42:30,381 INFO  [ckan.config.environment] Loading templates from /usr/src/ckan/templates
2022-09-22 14:42:30,534 CRITI [ckan.lib.uploader] Please specify a ckan.storage_path in your config
                        for your uploads
2022-09-22 14:42:30,708 WARNI [ckan.config.middleware.flask_app] Extensions are excluded from CSRF protection! We allow extensions to run without CSRF protection but it will be forced future releases. Read the documentation for more information on how to add CSRF protection to your extension.
============================================================================== test session starts ==============================================================================
platform linux -- Python 3.7.14, pytest-7.1.3, pluggy-1.0.0 -- /usr/local/bin/python
cachedir: .pytest_cache
rootdir: /usr/src, configfile: pyproject.toml, testpaths: ckan, ckanext
plugins: freezegun-0.4.2, split-0.8.0, test-groups-1.0.3, factoryboy-2.4.0, Faker-14.2.0, rerunfailures-10.2, cov-3.0.0
collected 2883 items
2022-09-22 14:42:45,763 INFO  [ckan.config.environment] Loading templates from /usr/src/ckan/templates
2022-09-22 14:42:46,353 INFO  [ckan.config.environment] Loading templates from /usr/src/ckan/templates

ckan/tests/test_authz.py::test_config_overrides_default PASSED                                                                                                            [  0%]
ckan/tests/test_authz.py::test_config_override_also_works_with_prefix PASSED                                                                                              [  0%]
ckan/tests/test_authz.py::test_unknown_permission_returns_false PASSED                                                                                                    [  0%]
ckan/tests/test_authz.py::test_unknown_permission_not_in_config_returns_false PASSED                                                                                      [  0%]
ckan/tests/test_authz.py::test_default_roles_`that_cascade`_to_sub_groups_is_a_list PASSED                                                                                [  0%]
...:
test-infrastructure$ ./teardown.sh
```

If you wish to run individual tests, it can be done with:
```
docker compose exec ckan pytest -vv --ckan-ini=test-core-ci.ini ckan/tests/lib/test_helpers.py::test_get_translated
```

## Known issues

* pytest-split causes testing errors.
* Windows
* Run as something other than root in the container
