# encoding: utf-8

from __future__ import annotations

import logging
import sys
import cgitb
import warnings
import traceback

import xml.dom.minidom
from typing import Collection, Any, Optional, Type, overload

import requests
from requests.auth import HTTPBasicAuth

import ckan.model as model
import ckan.model.domain_object as domain_object
import ckan.logic as logic
from ckan.types import Context

from ckan.lib.search.common import (
    make_connection, SearchIndexError, SearchQueryError,  # type: ignore
    SolrConnectionError, # type: ignore
    SearchError, is_available, SolrSettings, config
)
from ckan.lib.search.index import (
    SearchIndex, PackageSearchIndex, NoopSearchIndex
)
from ckan.lib.search.query import (
    SearchQuery,
    TagSearchQuery, ResourceSearchQuery, PackageSearchQuery,
    QueryOptions, convert_legacy_parameters_to_solr  # type: ignore
)
from ckan.lib.search.index import SearchIndex


log = logging.getLogger(__name__)


def text_traceback() -> str:
    info = sys.exc_info()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            text = cgitb.text(info)
        except RuntimeError:
            # there is werkzeug.local.LocalProxy object inside traceback, that
            # cannot be printed out by the cgitb
            res = "".join(traceback.format_tb(info[-1]))
        else:
            res = 'the original traceback:'.join(
                text.split('the original traceback:')[1:]
            ).strip()

    return res


SUPPORTED_SCHEMA_VERSIONS = ['2.8', '2.9', '2.10', '2.11']

DEFAULT_OPTIONS = {
    'limit': 20,
    'offset': 0,
    # about presenting the results
    'order_by': 'rank',
    'return_objects': False,
    'ref_entity_with_attr': 'name',
    'all_fields': False,
    'search_tags': True,
    'callback': None,  # simply passed through
}

_INDICES: dict[str, Type[SearchIndex]] = {
    'package': PackageSearchIndex
}

_QUERIES: dict[str, Type[SearchQuery]] = {
    'tag': TagSearchQuery,
    'resource': ResourceSearchQuery,
    'package': PackageSearchQuery
}

SOLR_SCHEMA_FILE_OFFSET_MANAGED = '/schema?wt=schema.xml'
SOLR_SCHEMA_FILE_OFFSET_CLASSIC = '/admin/file/?file=schema.xml'


def _normalize_type(_type: Any) -> str:
    if isinstance(_type, domain_object.DomainObject):
        _type = _type.__class__
    if isinstance(_type, type):
        _type = _type.__name__
    return _type.strip().lower()


@overload
def index_for(_type: Type[model.Package]) -> PackageSearchIndex: ...

@overload
def index_for(_type: Any) -> SearchIndex: ...

def index_for(_type: Any) -> SearchIndex:
    """ Get a SearchIndex instance sub-class suitable for
        the specified type. """
    try:
        _type_n = _normalize_type(_type)
        return _INDICES[_type_n]()
    except KeyError:
        log.warning("Unknown search type: %s", _type)
        return NoopSearchIndex()


@overload
def query_for(_type: Type[model.Package]) -> PackageSearchQuery:
    ...


@overload
def query_for(_type: Type[model.Resource]) -> ResourceSearchQuery:
    ...


@overload
def query_for(_type: Type[model.Tag]) -> TagSearchQuery:
    ...


def query_for(_type: Any) -> SearchQuery:
    """ Get a SearchQuery instance sub-class suitable for the specified
        type. """
    try:
        _type_n = _normalize_type(_type)
        return _QUERIES[_type_n]()
    except KeyError:
        raise SearchError("Unknown search type: %s" % _type)


def rebuild(package_id: Optional[str] = None,
            only_missing: bool = False,
            force: bool = False,
            defer_commit: bool = False,
            package_ids: Optional[Collection[str]] = None,
            quiet: bool = False,
            clear: bool = False):
    '''
        Rebuilds the search index.

        If a dataset id is provided, only this dataset will be reindexed.
        When reindexing all datasets, if only_missing is True, only the
        datasets not already indexed will be processed. If force equals
        True, if an exception is found, the exception will be logged, but
        the process will carry on.
    '''
    log.info("Rebuilding search index...")

    package_index = index_for(model.Package)
    context: Context = {
        'ignore_auth': True,
    }

    if package_id:
        log.info('Indexing just package %r...', package_id)
        logic.index_update_package(context, package_id)
    elif package_ids is not None:
        for package_id in package_ids:
            log.info('Indexing just package %r...', package_id)
            logic.index_update_package(context, package_id, True)
    else:
        packages = model.Session.query(model.Package.id)
        if config.get('ckan.search.remove_deleted_packages'):
            packages = packages.filter(model.Package.state != 'deleted')

        package_ids = [r[0] for r in packages.all()]

        if only_missing:
            log.info('Indexing only missing packages...')
            package_query = query_for(model.Package)
            indexed_pkg_ids = set(package_query.get_all_entity_ids(
                max_results=len(package_ids)))
            # Packages not indexed
            package_ids = set(package_ids) - indexed_pkg_ids

            if len(package_ids) == 0:
                log.info('All datasets are already indexed')
                return
        else:
            log.info('Rebuilding the whole index...')
            # When refreshing, the index is not previously cleared
            if clear:
                package_index.clear()

        total_packages = len(package_ids)
        for counter, pkg_id in enumerate(package_ids):
            if not quiet:
                sys.stdout.write(
                    "\rIndexing dataset {0}/{1}".format(
                        counter +1, total_packages)
                )
                sys.stdout.flush()
            try:
                logic.index_update_package(context, pkg_id, defer_commit)
            except Exception as e:
                log.error('Error while indexing dataset %s: %s',
                    pkg_id, repr(e))
                if force:
                    log.error(text_traceback())
                    continue
                else:
                    raise

    model.Session.commit()
    log.info('Finished rebuilding search index.')


def commit() -> None:
    package_index = index_for(model.Package)
    package_index.commit()
    log.info('Committed pending changes on the search index')


def check() -> None:
    package_query = query_for(model.Package)

    log.debug("Checking packages search index...")
    pkgs_q = model.Session.query(model.Package).filter_by(
        state=model.State.ACTIVE)
    pkgs = {pkg.id for pkg in pkgs_q}
    indexed_pkgs = set(package_query.get_all_entity_ids(max_results=len(pkgs)))
    pkgs_not_indexed = pkgs - indexed_pkgs
    print('Packages not indexed = %i out of %i' % (len(pkgs_not_indexed),
                                                   len(pkgs)))
    for pkg_id in pkgs_not_indexed:
        pkg = model.Session.get(model.Package, pkg_id)
        assert pkg
        print((pkg.metadata_modified.strftime('%Y-%m-%d'), pkg.name))


def show(package_reference: str) -> dict[str, Any]:
    package_query = query_for(model.Package)
    return package_query.get_index(package_reference)


def clear(package_reference: str) -> None:
    package_index = index_for(model.Package)
    log.debug("Clearing search index for dataset %s...",
              package_reference)
    package_index.delete_package({'id': package_reference})


def clear_all() -> None:
    package_index = index_for(model.Package)
    log.debug("Clearing search index...")
    package_index.clear()

def _get_schema_from_solr(file_offset: str):

    timeout = config.get('ckan.requests.timeout')

    solr_url, solr_user, solr_password = SolrSettings.get()

    url = solr_url.strip('/') + file_offset

    if solr_user is not None and solr_password is not None:
        response = requests.get(
            url,
            timeout=timeout,
            auth=HTTPBasicAuth(solr_user, solr_password))
    else:
        response = requests.get(url, timeout=timeout)

    return response

def check_solr_schema_version(schema_file: Optional[str]=None) -> bool:
    '''
        Checks if the schema version of the SOLR server is compatible
        with this CKAN version.

        The schema will be retrieved from the SOLR server, using the
        offset defined in SOLR_SCHEMA_FILE_OFFSET_MANAGED
        ('/schema?wt=schema.xml'). If SOLR is set to use the manually
        edited `schema.xml`, the schema will be retrieved from the SOLR
        server using the offset defined in
        SOLR_SCHEMA_FILE_OFFSET_CLASSIC ('/admin/file/?file=schema.xml').

        The schema_file parameter allows to override this pointing to
        different schema file, but it should only be used for testing
        purposes.

        If the CKAN instance is configured to not use SOLR or the SOLR
        server is not available, the function will return False, as the
        version check does not apply. If the SOLR server is available,
        a SearchError exception will be thrown if the version could not
        be extracted or it is not included in the supported versions list.

        :schema_file: Absolute path to an alternative schema file. Should
                      be only used for testing purposes (Default is None)
    '''

    if not is_available():
        # Something is wrong with the SOLR server
        log.warning('Problems were found while connecting to the SOLR server')
        return False

    # Try to get the schema XML file to extract the version
    if not schema_file:
        try:
            # Try Managed Schema
            res = _get_schema_from_solr(SOLR_SCHEMA_FILE_OFFSET_MANAGED)
            res.raise_for_status()
        except requests.HTTPError:
            # Fallback to Manually Edited schema.xml
            res = _get_schema_from_solr(SOLR_SCHEMA_FILE_OFFSET_CLASSIC)
        schema_content = res.text
    else:
        with open(schema_file, 'rb') as f:
            schema_content = f.read()

    tree = xml.dom.minidom.parseString(schema_content)

    # Up to CKAN 2.9 the schema version was stored in the `version` attribute.
    # Going forward, we are storing it in the `name` one in the form `ckan-X.Y`
    version = ''
    if tree.documentElement is not None:
        name_attr = tree.documentElement.getAttribute('name')
        if name_attr.startswith('ckan-'):
            version = name_attr.split('-')[1]
        else:
            version = tree.documentElement.getAttribute('version')

    if not len(version):
        msg = 'Could not extract version info from the SOLR schema'
        if schema_file:
            msg += ', using file {}'.format(schema_file)
        raise SearchError(msg)

    if not version in SUPPORTED_SCHEMA_VERSIONS:
        raise SearchError('SOLR schema version not supported: %s. Supported'
                          ' versions are [%s]'
                          % (version, ', '.join(SUPPORTED_SCHEMA_VERSIONS)))
    return True
