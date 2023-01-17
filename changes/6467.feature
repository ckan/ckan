:ref:`declare-config-options`: declare configuration options to ensure validation and default values.

All the native config options from CKAN are validated and converted to the
expected type during application startup. That's how change the behavior::

    debug = config.get("debug")

    # CKAN <= v2.9
    assert type(debug) is str
    assert debug == "false" # or any value that is specified in the config file

    # CKAN >= v2.10
    assert type(debug) is bool
    assert debug is False # or ``True``

If you are using ``aslist``, ``asbool``, ``asint`` convertes from
``ckan.plugins.toolkit``, nothing will change, because they are idempotent::

    # produces the same result in v2.9 and v2.10
    assesrt tk.asbool(config.get("debug")) is False
    assesrt tk.asint(config.get("devserver.port")) == 5000
    assesrt tk.aslist(config.get("ckan.plugins")) == ["stats"]

If you are using custom logic, the code requires a review. For example, the
following will produce an ``AttributeError``, because ``ckan.plugins`` is
converted into a list during application's startup::

    # AttributeError
    plugins = config.get("ckan.plugins").split()

Depending on desired backward compatibility, one of the following expressions
can be used instead::

    # if both v2.9 and v2.10 are supported
    plugins = tk.aslist(config.get("ckan.plugins"))

    # if only v2.10 is supported
    plugins = config.get("ckan.plugins")

The second major change affects default values. Starting from CKAN v2.10,
majority of the config options has a declared default value. It means that
whenever you invoke ``config.get`` method, the **declared default** value is
returned instead of ``None``. Example::

    # CKAN v2.9
    assert config.get("search.facets.limit") is None

    # CKAN v2.10
    assert config.get("search.facets.limit") == 10

The second argument to ``config.get`` is used only when you are trying to get
the value of the missing **undeclared** option::

    assert config.get("not.declared.and.missing.from.config", 1) == 1


The above is the same for any extension that **declares** its config options
using ``IConfigDeclaration`` interface or ``config_declarations`` blanket.
