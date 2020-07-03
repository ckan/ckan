API Tokens: an alternative to API keys. Tokens can be created and
removed on demand(check :ref:`api authentication>`) and there is no
restriction on the maximum number of tokens per user. Consider using
tokens instead of API keys and create a separate token for each
use-case instead of sharing the same token between multiple
clients. By default API Tokens are JWT, but the goal is to make them
as customizable as possible, so alternative formats can be implemented
using `ckan.plugins.interfaces.IApiToken` interface.
