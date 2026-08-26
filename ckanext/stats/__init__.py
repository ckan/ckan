# workaround for compatibility with setuptools<82
# see https://github.com/ckan/ckan/discussions/9340
try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    pass
