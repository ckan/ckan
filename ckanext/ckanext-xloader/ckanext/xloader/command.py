# -*- coding: utf-8 -*-

import sys
import logging
import ckan.plugins.toolkit as tk

from ckanext.xloader.jobs import xloader_data_into_datastore_
from ckanext.xloader.utils import XLoaderFormats


class XloaderCmd:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.error_occured = False

    def _setup_xloader_logger(self):
        # whilst the development.ini's loggers are setup now, because this is
        # cli, let's ensure we xloader debug messages are printed for the user
        logger = logging.getLogger('ckanext.xloader')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '      %(name)-12s %(levelname)-5s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # in case the config

    def _submit_all_existing(self, sync=False, queue=None):
        from ckanext.datastore.backend \
            import get_all_resources_ids_in_datastore
        resource_ids = get_all_resources_ids_in_datastore()
        print('Processing %d resources' % len(resource_ids))
        user = tk.get_action('get_site_user')(
            {'ignore_auth': True}, {})
        for resource_id in resource_ids:
            try:
                resource_dict = tk.get_action('resource_show')(
                    {'ignore_auth': True}, {'id': resource_id})
            except tk.ObjectNotFound:
                print('  Skipping resource {} found in datastore but not in '
                      'metadata'.format(resource_id))
                continue
            self._submit_resource(resource_dict, user, indent=2, sync=sync, queue=queue)

    def _submit_all(self, sync=False, queue=None):
        # submit every package
        # for each package in the package list,
        #   submit each resource w/ _submit_package
        package_list = tk.get_action('package_search')(
            {'ignore_auth': True}, {'include_private': True, 'rows': 1000})
        package_list = [pkg['id'] for pkg in package_list['results']]
        print('Processing %d datasets' % len(package_list))
        user = tk.get_action('get_site_user')(
            {'ignore_auth': True}, {})
        for p_id in package_list:
            self._submit_package(p_id, user, indent=2, sync=sync, queue=queue)

    def _submit_package(self, pkg_id, user=None, indent=0, sync=False, queue=None):
        indentation = ' ' * indent
        if not user:
            user = tk.get_action('get_site_user')(
                {'ignore_auth': True}, {})

        try:
            pkg = tk.get_action('package_show')(
                {'ignore_auth': True},
                {'id': pkg_id.strip()})
        except Exception as e:
            print(e)
            print(indentation + 'Dataset "{}" was not found'.format(pkg_id))
            sys.exit(1)

        print(indentation + 'Processing dataset {} with {} resources'.format(
              pkg['name'], len(pkg['resources'])))
        for resource in pkg['resources']:
            try:
                resource['package_name'] = pkg['name']  # for debug output
                self._submit_resource(resource, user, indent=indent + 2, sync=sync, queue=queue)
            except Exception as e:
                self.error_occured = True
                print(str(e))
                print(indentation + 'ERROR submitting resource "{}" '.format(
                    resource['id']))
                continue

    def _submit_resource(self, resource, user, indent=0, sync=False, queue=None):
        '''resource: resource dictionary
        '''
        indentation = ' ' * indent

        if not XLoaderFormats.is_it_an_xloader_format(resource['format']):
            print(indentation
                  + 'Skipping resource {r[id]} because format "{r[format]}" is '
                  'not configured to be xloadered'.format(r=resource))
            return
        if resource['url_type'] in ('datapusher', 'xloader'):
            print(indentation
                  + 'Skipping resource {r[id]} because url_type "{r[url_type]}" '
                  'means resource.url points to the datastore '
                  'already, so loading would be circular.'.format(
                      r=resource))
            return
        dataset_ref = resource.get('package_name', resource['package_id'])
        print('{indent}{sync_style} /dataset/{dataset}/resource/{r[id]}\n'
              '{indent}           url={r[url]}\n'
              '{indent}           format={r[format]}'
              .format(sync_style='Processing' if sync else 'Submitting',
                      dataset=dataset_ref, r=resource, indent=indentation))
        if self.dry_run:
            print(indentation + '(not submitted - dry-run)')
            return
        data_dict = {
            'resource_id': resource['id'],
            'ignore_hash': True,
        }
        if sync:
            data_dict['ckan_url'] = tk.config.get('ckan.site_url')
            input_dict = {
                'metadata': data_dict,
                'api_key': 'TODO'
            }
            logger = logging.getLogger('ckanext.xloader.cli')
            xloader_data_into_datastore_(input_dict, None, logger)
        else:
            if queue:
                data_dict['queue'] = queue
            success = tk.get_action('xloader_submit')({'user': user['name']}, data_dict)
            if success:
                print(indentation + '...ok')
            else:
                print(indentation + 'ERROR submitting resource')
                self.error_occured = True

    def print_status(self):
        import ckan.lib.jobs as rq_jobs
        jobs = rq_jobs.get_queue().jobs
        if not jobs:
            print('No jobs currently queued')
        for job in jobs:
            job_params = eval(job.description.replace(
                'ckanext.xloader.jobs.xloader_data_into_datastore', ''))
            job_metadata = job_params['metadata']
            print('{id} Enqueued={enqueued:%Y-%m-%d %H:%M} res_id={res_id} '
                  'url={url}'.format(
                      id=job._id,
                      enqueued=job.enqueued_at,
                      res_id=job_metadata['resource_id'],
                      url=job_metadata['original_url'],
                  ))
