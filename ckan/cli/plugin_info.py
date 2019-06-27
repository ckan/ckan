import click

@click.command(name=u'plugin-info', short_help='Provide info on installed plugins.')
def plugin_info():
    ''' print info about current plugins from the .ini file'''
    import ckan.plugins as p
    interfaces = {}
    plugins = {}
    for name in dir(p):
        item = getattr(p, name)
        try:
            if issubclass(item, p.Interface):
                interfaces[item] = {'class': item}
        except TypeError:
            pass

    for interface in interfaces:
        for plugin in p.PluginImplementations(interface):
            name = plugin.name
            if name not in plugins:
                plugins[name] = {'doc': plugin.__doc__,
                                    'class': plugin,
                                    'implements': []}
            plugins[name]['implements'].append(interface.__name__)

    for plugin in plugins:
        p = plugins[plugin]
        click.echo(plugin + ':')
        click.echo('-' * (len(plugin) + 1))
        if p['doc']:
            click.echo(p['doc'])
        click.echo('Implements:')
        for i in p['implements']:
            extra = None
            if i == 'ITemplateHelpers':
                extra = _template_helpers(p['class'])
            if i == 'IActions':
                extra = _actions(p['class'])
            click.echo('    {i}'.format(i=i))
            if extra:
                click.echo(extra)
        click.echo()

def _template_helpers(cls):
    ''' Return readable helper function info. '''
    helpers = cls.get_helpers()
    return _function_info(helpers)

def _actions(self, cls):
    ''' Return readable action function info. '''
    actions = cls.get_actions()
    return _function_info(actions)

def _function_info(functions):
    ''' Take a dict of functions and output readable info '''
    import inspect
    output = []
    for function_name in functions:
        fn = functions[function_name]
        args_info = inspect.getargspec(fn)
        params = args_info.args
        num_params = len(params)
        if args_info.varargs:
            params.append('*' + args_info.varargs)
        if args_info.keywords:
            params.append('**' + args_info.keywords)
        if args_info.defaults:
            offset = num_params - len(args_info.defaults)
            for i, v in enumerate(args_info.defaults):
                params[i + offset] = params[i + offset] + '=' + repr(v)
        # is this a classmethod if so remove the first parameter
        if inspect.ismethod(fn) and inspect.isclass(fn.__self__):
            params = params[1:]
        params = ', '.join(params)
        output.append('        {function_name}({params})'.format(
            function_name=function_name, params=params))
        # doc string
        if fn.__doc__:
            bits = fn.__doc__.split('\n')
            for bit in bits:
                output.append('            {bit}'.format(bit=bit))
    return ('\n').join(output)
