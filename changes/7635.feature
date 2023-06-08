``ckan generate fake-data`` accepts ``--user`` option that is used as ``context["user"]``.
Some factories(``api-token`` for example), have a special meaning for the ``user`` parameter
and do not pass it to context.
