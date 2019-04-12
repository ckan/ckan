# encoding: utf-8

import re

from pylons.util import PylonsInstaller

import ckan


class CKANInstaller(PylonsInstaller):

    def config_content(self, command, vars):
        ckan_version = ckan.__version__
        ckan_base_version = re.sub(r'[^0-9\.]', '', ckan_version)
        if ckan_base_version == ckan_version:
            ckan_doc_version = 'ckan-{0}'.format(ckan_version)
        else:
            ckan_doc_version = 'latest'

        vars.setdefault('doc_version', ckan_doc_version)

        return super(CKANInstaller, self).config_content(command, vars)
