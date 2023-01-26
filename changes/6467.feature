:ref:`declare-config-options`: declare configuration options to ensure validation and default values.

All the CKAN configuration options are validated and converted to the
expected type during the application startup. That's how the behavior has changed::

    debug = config.get("debug")

    # CKAN <= v2.9
    assert type(debug) is str
    assert debug == "false" # or any value that is specified in the config file

    # CKAN >= v2.10
    assert type(debug) is bool
    assert debug is False # or ``True``

The ``aslist``, ``asbool``, ``asint`` converters from ``ckan.plugins.toolkit`` will keep the current behaviour::

    # produces the same result in v2.9 and v2.10
    assert tk.asbool(config.get("debug")) is False
    assert tk.asint(config.get("ckan.devserver.port")) == 5000
    assert tk.aslist(config.get("ckan.plugins")) == ["stats"]

If you are using custom logic, the code requires a review. For example, the
following code will produce an ``AttributeError`` exception, because ``ckan.plugins`` is
converted into a list during the application's startup::

    # AttributeError
    plugins = config.get("ckan.plugins").split()

Depending on the desired backward compatibility, one of the following expressions
can be used instead::

    # if both v2.9 and v2.10 are supported
    plugins = tk.aslist(config.get("ckan.plugins"))

    # if only v2.10 is supported
    plugins = config.get("ckan.plugins")

The second major change affects default values for configuration options. Starting from CKAN 2.10,
the majority of the config options have a declared default value. It means that
whenever you invoke ``config.get`` method, the *declared default* value is
returned instead of ``None``. Example::

    # CKAN v2.9
    assert config.get("search.facets.limit") is None

    # CKAN v2.10
    assert config.get("search.facets.limit") == 10

The second argument to ``config.get`` should be only used to get
the value of a missing *undeclared* option::

    assert config.get("not.declared.and.missing.from.config", 1) == 1

The above is the same for any extension that *declares* its config options
using ``IConfigDeclaration`` interface or ``config_declarations`` blanket.
