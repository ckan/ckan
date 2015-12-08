import csv

import ckan.model as model
from ckan.common import json, OrderedDict


class SimpleDumper(object):
    '''Dumps just package data but including tags, groups, license text etc'''
    def dump(self, dump_file_obj, format='json', query=None):
        if query is None:
            query = model.Session.query(model.Package)
            active = model.State.ACTIVE
            query = query.filter_by(state=active)
        if format == 'csv':
            self.dump_csv(dump_file_obj, query)
        elif format == 'json':
            self.dump_json(dump_file_obj, query)
        else:
            raise Exception('Unknown format: %s' % format)

    def dump_csv(self, dump_file_obj, query):
        row_dicts = []
        for pkg in query:
            pkg_dict = pkg.as_dict()
            # flatten dict
            for name, value in pkg_dict.items()[:]:
                if isinstance(value, (list, tuple)):
                    if value and isinstance(value[0], dict) and \
                            name == 'resources':
                        for i, res in enumerate(value):
                            prefix = 'resource-%i' % i
                            pkg_dict[prefix + '-url'] = res['url']
                            pkg_dict[prefix + '-format'] = res['format']
                            pkg_dict[prefix + '-description'] = \
                                res['description']
                    else:
                        pkg_dict[name] = ' '.join(value)
                if isinstance(value, dict):
                    for name_, value_ in value.items():
                        pkg_dict[name_] = value_
                    del pkg_dict[name]
            row_dicts.append(pkg_dict)
        writer = CsvWriter(row_dicts)
        writer.save(dump_file_obj)

    def dump_json(self, dump_file_obj, query):
        pkgs = []
        for pkg in query:
            pkg_dict = pkg.as_dict()
            pkgs.append(pkg_dict)
        json.dump(pkgs, dump_file_obj, indent=4)


class CsvWriter:
    def __init__(self, package_dict_list=None):
        self._rows = []
        self._col_titles = []
        for row_dict in package_dict_list:
            for key in row_dict.keys():
                if key not in self._col_titles:
                    self._col_titles.append(key)
        for row_dict in package_dict_list:
            self._add_row_dict(row_dict)

    def _add_row_dict(self, row_dict):
        row = []
        for title in self._col_titles:
            if title in row_dict:
                if isinstance(row_dict[title], int):
                    row.append(row_dict[title])
                elif isinstance(row_dict[title], unicode):
                    row.append(row_dict[title].encode('utf8'))
                else:
                    row.append(row_dict[title])
            else:
                row.append(None)
        self._rows.append(row)

    def save(self, file_obj):
        writer = csv.writer(file_obj, quotechar='"',
                            quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(self._col_titles)
        for row in self._rows:
            writer.writerow(row)


class UserDumper(object):
    def dump(self, dump_file_obj):
        query = model.Session.query(model.User)
        query = query.order_by(model.User.created.asc())

        columns = (('id', 'name', 'openid', 'fullname', 'email', 'created',
                    'about'))
        row_dicts = []
        for user in query:
            row = OrderedDict()
            for col in columns:
                value = getattr(user, col)
                if not value:
                    value = ''
                if col == 'created':
                    value = str(value)  # or maybe dd/mm/yyyy?
                row[col] = value
            row_dicts.append(row)

        writer = CsvWriter(row_dicts)
        writer.save(dump_file_obj)
        dump_file_obj.close()
