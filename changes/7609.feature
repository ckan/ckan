:py:class:`~ckan.plugins.interfaces.Interface` has
`_reverse_iteration_order` property. When it set to `True`,
:py:class:`~ckan.plugins.core.PluginImplementations(interface)` will traverse
plugins implementing the interface in reverse order.

Interfaces that are traversed in reverse order:

* IApiToken
* IConfigDeclaration
* IConfigurer
* ITranslation
* IValidators
