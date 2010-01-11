import difflib

import ckan.model as model
import vdm

ignore_keys = ('id', 'revision')

class Differ(object):
    def diff(self, obj_a, obj_b):
        assert isinstance(obj_a, vdm.sqlalchemy.StatefulObjectMixin), obj_a
        assert isinstance(obj_b, vdm.sqlalchemy.StatefulObjectMixin), obj_b

        dicts = [obj_a.__dict__, obj_b.__dict__]
        keys = dicts[0].keys()
        assert keys == dicts[1].keys()

        diffs = {}

        # Make specific fields more readable
        if 'license_id' in keys:
            for dict_ in dicts:
                dict_['license'] = model.Session.query(model.License).get(dict_['license_id']).name if \
                                   dict_['license_id'] else None

        # Diff each field
        keys = dicts[0].keys()
        for key in keys:
            if key.startswith('_') or key.endswith('_id') or key in ignore_keys:
                continue
            # None --> ''
            values = [dict_[key] if dict_[key] is not None else u'' for dict_ in dicts]
            # Choose differ
            print values
            if '\n' in values[0] or '\n' in values[1]:
                record_differ = self._multi_line_text_record_differ
            else:
                record_differ = self._default_record_differ
            # Do the diff
            diff = record_differ(values[0], values[1])
            # Record the diff
            if diff:
                diffs[key] = diff

        return diffs

    def _multi_line_text_record_differ(self, a, b):
        if a != b:
            return '\n'.join(difflib.Differ().compare(a.split('\n'), b.split('\n')))
        else:
            return None

    def _default_record_differ(self, a, b):
        return self._multi_line_text_record_differ(a, b)

