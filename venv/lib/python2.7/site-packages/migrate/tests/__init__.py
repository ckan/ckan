# make this package available during imports as long as we support <python2.5
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from unittest import TestCase
import migrate
import six


class TestVersionDefined(TestCase):
    def test_version(self):
        """Test for migrate.__version__"""
        self.assertTrue(isinstance(migrate.__version__, six.string_types))
        self.assertTrue(len(migrate.__version__) > 0)
