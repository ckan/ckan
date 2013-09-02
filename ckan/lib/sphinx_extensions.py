# coding=UTF-8
import re

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.util.compat import Directive

import ckan.lib.config as lib_config
from paste.deploy.converters import asbool


def setup(app):
    app.add_config_value('config', False, False)
    app.add_node(config)
    app.add_directive('config', ConfigDirective)


class config(nodes.General, nodes.Element):
    pass


class ConfigDirective(Directive):
    ''' This is the config documentor it can be used to add all config
    settings to the docs or just ones specified.

    .. config::

    .. config:: section section2

    '''

    has_content = True
    required_arguments = 0
    optional_arguments = 50
    final_argument_whitespace = True

    config_options = {}
    config_sections = {}

    def build_config_nodes(self):

        def slug(name):
            return re.sub('[^A-Za-z0-9]', '-', name)

        def make_para(arg):
            def build_para(arg):
                parts = re.split('(?<=:)(:\n+.*$)', arg,
                                 flags=re.DOTALL | re.MULTILINE)
                n = []
                for part in parts:
                    if part.startswith(':\n'):
                        n += [nodes.literal_block('', part[1:].strip())]
                    else:
                        node = nodes.paragraph()
                        node.document = self.state.document
                        self.state.nested_parse(ViewList([part]), 0, node)
                        n += [node]
                return [nodes.paragraph('', '', *n)]

            if not arg:
                return []
            parts = re.split('(?<=[^:])\n\n', arg)

            nodes_list = []
            for part in parts:
                nodes_list += build_para(part)
            return nodes_list

        def setting_node(name, item):
            deprecated = item.get('undocumented', False)
            if asbool(deprecated):
                return []

            n = [nodes.title('', name)]

            deprecated = item.get('deprecated')
            if deprecated:
                dep_text = 'This setting was deprecated in version %s'
                admonition = nodes.admonition(
                    'deprecated',
                    nodes.title('', 'Deprecated'),
                    nodes.paragraph('', dep_text % deprecated)
                )
                admonition['classes'] += ['deprecated', 'warning']
                n += [admonition]

            description = item.get('description')
            n += make_para(description)

            default = item.get('default')
            if default:
                n += [nodes.paragraph('', 'Default value: ',
                                      nodes.literal('', default))]

            type_ = item.get('type')
            if type_:
                n += [nodes.paragraph('', 'Type: ', nodes.literal('', type_))]
            example = item.get('example')
            if example:
                n += [nodes.paragraph('', 'Example:'),
                      nodes.literal_block('', example)]

            node = [nodes.section('', *n,
                    ids=[slug(name)])]
            return node

        def section_items(item):
            n = []
            items = item['options']
            for item_ in items:
                node = self.config_options[item_]
                n += node
            return n

        def section_node(item):

            title = item.get('title', '')
            n = [nodes.title('', title)]
            description = item.get('description')
            if description:
                n += make_para(description)

            items = item['options']
            for item_ in items:
                node = self.config_options[item_]
                n += node

            node = [nodes.section('',
                    *n,
                    ids=[slug(title)])]
            return node

        items = lib_config.config_sections
        for item in items:
            self.config_sections[item['name']] = {'detail': item, 'nodes': {}}
        items = lib_config.config_details
        for item in items:
            node = setting_node(item, items[item])
            self.config_options[item] = node
            section = items[item].get('section')
            if section in self.config_sections:
                self.config_sections[section]['nodes'][item] = node

        items = lib_config.config_sections
        for item in items:
            self.config_sections[item['name']]['full_node'] = \
                section_node(item)
            self.config_sections[item['name']]['node'] = section_items(item)

    def run(self):

        self.reporter = self.state.document.reporter
        self.env = self.state.document.settings.env
        self.warnings = []
        self.result = ViewList()
        self.build_config_nodes()

        include_section = True
        if self.arguments:
            include_section = False
            sections = self.arguments
        else:
            sections = [s['name'] for s in lib_config.config_sections]

        nodes_list = []
        for section in sections:
            sec = self.config_sections[section]
            if include_section:
                nodes_list.extend(sec['full_node'])
            else:
                nodes_list.extend(sec['node'])
        return nodes_list
