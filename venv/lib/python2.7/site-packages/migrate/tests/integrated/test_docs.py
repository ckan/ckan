import doctest
import os


from migrate.tests import fixture

# Collect tests for all handwritten docs: doc/*.rst

dir = ('..','..','..','doc','source')
absdir = (os.path.dirname(os.path.abspath(__file__)),)+dir
dirpath = os.path.join(*absdir)
files = [f for f in os.listdir(dirpath) if f.endswith('.rst')]
paths = [os.path.join(*(dir+(f,))) for f in files]
assert len(paths) > 0
suite = doctest.DocFileSuite(*paths)

def test_docs():
    suite.debug()
