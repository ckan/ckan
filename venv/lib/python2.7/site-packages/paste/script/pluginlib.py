from __future__ import print_function
# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import os
import pkg_resources

def add_plugin(egg_info_dir, plugin_name):
    """
    Add the plugin to the given distribution (or spec), in
    .egg-info/paster_plugins.txt
    """
    fn = os.path.join(egg_info_dir, 'paster_plugins.txt')
    if not os.path.exists(fn):
        lines = []
    else:
        f = open(fn)
        lines = [l.strip() for l in f.readlines() if l.strip()]
        f.close()
    if plugin_name in lines:
        # Nothing to do
        return
    lines.append(plugin_name)
    if not os.path.exists(os.path.dirname(fn)):
        os.makedirs(os.path.dirname(fn))
    f = open(fn, 'w')
    for line in lines:
        f.write(line)
        f.write('\n')
    f.close()

def remove_plugin(egg_info_dir, plugin_name):
    """
    Remove the plugin to the given distribution (or spec), in
    .egg-info/paster_plugins.txt.  Raises ValueError if the
    plugin is not in the file.
    """
    fn = os.path.join(egg_info_dir, 'paster_plugins.txt')
    if not os.path.exists(fn):
        raise ValueError(
            "Cannot remove plugin from %s; file does not exist"
            % fn)
    f = open(fn)
    lines = [l.strip() for l in f.readlines() if l.strip()]
    f.close()
    for line in lines:
        # What about version specs?
        if line.lower() == plugin_name.lower():
            break
    else:
        raise ValueError(
            "Plugin %s not found in file %s (from: %s)"
            % (plugin_name, fn, lines))
    lines.remove(line)
    print('writing', lines)
    f = open(fn, 'w')
    for line in lines:
        f.write(line)
        f.write('\n')
    f.close()

def find_egg_info_dir(dir):
    while 1:
        try:
            filenames = os.listdir(dir)
        except OSError:
            # Probably permission denied or something
            return None
        for fn in filenames:
            if (fn.endswith('.egg-info')
                and os.path.isdir(os.path.join(dir, fn))):
                return os.path.join(dir, fn)
        parent = os.path.dirname(dir)
        if parent == dir:
            # Top-most directory
            return None
        dir = parent

def resolve_plugins(plugin_list):
    found = []
    while plugin_list:
        plugin = plugin_list.pop()
        try:
            pkg_resources.require(plugin)
        except pkg_resources.DistributionNotFound as e:
            msg = '%sNot Found%s: %s (did you run python setup.py develop?)'
            if str(e) != plugin:
                e.args = (msg % (str(e) + ': ', ' for', plugin)),
            else:
                e.args = (msg % ('', '', plugin)),
            raise
        found.append(plugin)
        dist = get_distro(plugin)
        if dist.has_metadata('paster_plugins.txt'):
            data = dist.get_metadata('paster_plugins.txt')
            for add_plugin in parse_lines(data):
                if add_plugin not in found:
                    plugin_list.append(add_plugin)
    return list(map(get_distro, found))

def get_distro(spec):
    return pkg_resources.get_distribution(spec)

def load_commands_from_plugins(plugins):
    commands = {}
    for plugin in plugins:
        commands.update(pkg_resources.get_entry_map(
            plugin, group='paste.paster_command'))
    return commands

def parse_lines(data):
    result = []
    for line in data.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            result.append(line)
    return result

def load_global_commands():
    commands = {}
    for p in pkg_resources.iter_entry_points('paste.global_paster_command'):
        commands[p.name] = p
    return commands

def egg_name(dist_name):
    return pkg_resources.to_filename(pkg_resources.safe_name(dist_name))

def egg_info_dir(base_dir, dist_name):
    all = []
    for dir_extension in ['.'] + os.listdir(base_dir):
        full = os.path.join(base_dir, dir_extension,
                            egg_name(dist_name)+'.egg-info')
        all.append(full)
        if os.path.exists(full):
            return full
    raise IOError("No egg-info directory found (looked in %s)"
                  % ', '.join(all))
