API Tokens: an alternative to API keys. Tokens can be created and
removed on demand(check :ref:`api authentication>`) and there is no
restriction on the maximum number of tokens per user. Consider using
it instead of them API key and prefer the creation of a separate token for
each use-case instead of sharing the same token between multiple
clients. In original implementation API Tokens are JWT, but the goal
is to make them as customizable as possible, so alternative formats
can be implemented using
:py:class:`~ckan.plugins.interfaces.IApiToken` interface.
