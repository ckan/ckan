# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
import os
import pkg_resources
from six.moves import input
from six.moves.urllib.parse import quote
import string
import cgi

Cheetah = None
try:
    import subprocess
except ImportError:
    subprocess = None # jython
import inspect

class SkipTemplate(Exception):
    """
    Raised to indicate that the template should not be copied over.
    Raise this exception during the substitution of your template
    """

def copy_dir(source, dest, vars, verbosity, simulate, indent=0,
             use_cheetah=False, sub_vars=True, interactive=False,
             svn_add=True, overwrite=True, template_renderer=None):
    """
    Copies the ``source`` directory to the ``dest`` directory.

    ``vars``: A dictionary of variables to use in any substitutions.

    ``verbosity``: Higher numbers will show more about what is happening.

    ``simulate``: If true, then don't actually *do* anything.

    ``indent``: Indent any messages by this amount.

    ``sub_vars``: If true, variables in ``_tmpl`` files and ``+var+``
    in filenames will be substituted.

    ``use_cheetah``: If true, then any templates encountered will be
    substituted with Cheetah.  Otherwise ``template_renderer`` or
    ``string.Template`` will be used for templates.

    ``svn_add``: If true, any files written out in directories that are part of
    a svn working copy will be added (via ``svn add``).

    ``overwrite``: If false, then don't every overwrite anything.

    ``interactive``: If you are overwriting a file and interactive is
    true, then ask before overwriting.

    ``template_renderer``: This is a function for rendering templates
    (if you don't want to use Cheetah or string.Template).  It should
    have the signature ``template_renderer(content_as_string,
    vars_as_dict, filename=filename)``.
    """
    # This allows you to use a leading +dot+ in filenames which would
    # otherwise be skipped because leading dots make the file hidden:
    vars.setdefault('dot', '.')
    vars.setdefault('plus', '+')
    use_pkg_resources = isinstance(source, tuple)
    if use_pkg_resources:
        names = pkg_resources.resource_listdir(source[0], source[1])
    else:
        names = os.listdir(source)
    names.sort()
    pad = ' '*(indent*2)
    if not os.path.exists(dest):
        if verbosity >= 1:
            print('%sCreating %s/' % (pad, dest))
        if not simulate:
            svn_makedirs(dest, svn_add=svn_add, verbosity=verbosity,
                         pad=pad)
    elif verbosity >= 2:
        print('%sDirectory %s exists' % (pad, dest))
    for name in names:
        if use_pkg_resources:
            full = '/'.join([source[1], name])
        else:
            full = os.path.join(source, name)
        reason = should_skip_file(name)
        if reason:
            if verbosity >= 2:
                reason = pad + reason % {'filename': full}
                print(reason)
            continue
        if sub_vars:
            dest_full = os.path.join(dest, substitute_filename(name, vars))
        sub_file = False
        if dest_full.endswith('_tmpl'):
            dest_full = dest_full[:-5]
            sub_file = sub_vars
        if use_pkg_resources and pkg_resources.resource_isdir(source[0], full):
            if verbosity:
                print('%sRecursing into %s' % (pad, os.path.basename(full)))
            copy_dir((source[0], full), dest_full, vars, verbosity, simulate,
                     indent=indent+1, use_cheetah=use_cheetah,
                     sub_vars=sub_vars, interactive=interactive,
                     svn_add=svn_add, template_renderer=template_renderer)
            continue
        elif not use_pkg_resources and os.path.isdir(full):
            if verbosity:
                print('%sRecursing into %s' % (pad, os.path.basename(full)))
            copy_dir(full, dest_full, vars, verbosity, simulate,
                     indent=indent+1, use_cheetah=use_cheetah,
                     sub_vars=sub_vars, interactive=interactive,
                     svn_add=svn_add, template_renderer=template_renderer)
            continue
        elif use_pkg_resources:
            content = pkg_resources.resource_string(source[0], full)
        else:
            with open(full, 'r') as f:
                content = f.read()
        if sub_file:
            try:
                content = substitute_content(content, vars, filename=full,
                                             use_cheetah=use_cheetah,
                                             template_renderer=template_renderer)
            except SkipTemplate:
                continue
            if content is None:
                continue
        already_exists = os.path.exists(dest_full)
        if already_exists:
            f = open(dest_full, 'rb')
            old_content = f.read()
            f.close()
            if old_content == content:
                if verbosity:
                    print('%s%s already exists (same content)' % (pad, dest_full))
                continue
            if interactive:
                if not query_interactive(
                    full, dest_full, content, old_content,
                    simulate=simulate):
                    continue
            elif not overwrite:
                continue
        if verbosity and use_pkg_resources:
            print('%sCopying %s to %s' % (pad, full, dest_full))
        elif verbosity:
            print('%sCopying %s to %s' % (pad, os.path.basename(full), dest_full))
        if not simulate:
            with open(dest_full, 'w') as f:
                f.write(content)
        if svn_add and not already_exists:
            if os.system('svn info %r >/dev/null 2>&1' % os.path.dirname(os.path.abspath(dest_full))) > 0:
                if verbosity > 1:
                    print('%sNot part of a svn working copy; cannot add file' % pad)
            else:
                cmd = ['svn', 'add', dest_full]
                if verbosity > 1:
                    print('%sRunning: %s' % (pad, ' '.join(cmd)))
                if not simulate:
                    # @@: Should
                    if subprocess is None:
                        raise RuntimeError('copydir failed, environment '
                                           'does not support subprocess '
                                           'module')
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    stdout, stderr = proc.communicate()
                    if verbosity > 1 and stdout:
                        print('Script output:')
                        print(stdout)
        elif svn_add and already_exists and verbosity > 1:
            print('%sFile already exists (not doing svn add)' % pad)

def should_skip_file(name):
    """
    Checks if a file should be skipped based on its name.

    If it should be skipped, returns the reason, otherwise returns
    None.
    """
    if name.startswith('.'):
        return 'Skipping hidden file %(filename)s'
    if name.endswith('~') or name.endswith('.bak'):
        return 'Skipping backup file %(filename)s'
    if name.endswith('.pyc') or name.endswith('.pyo'):
        return 'Skipping %s file %%(filename)s' % os.path.splitext(name)[1]
    if name.endswith('$py.class'):
        return 'Skipping $py.class file %(filename)s'
    if name in ('CVS', '_darcs'):
        return 'Skipping version control directory %(filename)s'
    return None

# Overridden on user's request:
all_answer = None

def query_interactive(src_fn, dest_fn, src_content, dest_content,
                      simulate):
    global all_answer
    from difflib import unified_diff, context_diff
    u_diff = list(unified_diff(
        dest_content.splitlines(),
        src_content.splitlines(),
        dest_fn, src_fn))
    c_diff = list(context_diff(
        dest_content.splitlines(),
        src_content.splitlines(),
        dest_fn, src_fn))
    added = len([l for l in u_diff if l.startswith('+')
                   and not l.startswith('+++')])
    removed = len([l for l in u_diff if l.startswith('-')
                   and not l.startswith('---')])
    if added > removed:
        msg = '; %i lines added' % (added-removed)
    elif removed > added:
        msg = '; %i lines removed' % (removed-added)
    else:
        msg = ''
    print('Replace %i bytes with %i bytes (%i/%i lines changed%s)' % (
        len(dest_content), len(src_content),
        removed, len(dest_content.splitlines()), msg))
    prompt = 'Overwrite %s [y/n/d/B/?] ' % dest_fn
    while 1:
        if all_answer is None:
            response = input(prompt).strip().lower()
        else:
            response = all_answer
        if not response or response[0] == 'b':
            import shutil
            new_dest_fn = dest_fn + '.bak'
            n = 0
            while os.path.exists(new_dest_fn):
                n += 1
                new_dest_fn = dest_fn + '.bak' + str(n)
            print('Backing up %s to %s' % (dest_fn, new_dest_fn))
            if not simulate:
                shutil.copyfile(dest_fn, new_dest_fn)
            return True
        elif response.startswith('all '):
            rest = response[4:].strip()
            if not rest or rest[0] not in ('y', 'n', 'b'):
                print(query_usage)
                continue
            response = all_answer = rest[0]
        if response[0] == 'y':
            return True
        elif response[0] == 'n':
            return False
        elif response == 'dc':
            print('\n'.join(c_diff))
        elif response[0] == 'd':
            print('\n'.join(u_diff))
        else:
            print(query_usage)

query_usage = """\
Responses:
  Y(es):    Overwrite the file with the new content.
  N(o):     Do not overwrite the file.
  D(iff):   Show a unified diff of the proposed changes (dc=context diff)
  B(ackup): Save the current file contents to a .bak file
            (and overwrite)
  Type "all Y/N/B" to use Y/N/B for answer to all future questions
"""

def svn_makedirs(dir, svn_add, verbosity, pad):
    parent = os.path.dirname(os.path.abspath(dir))
    if not os.path.exists(parent):
        svn_makedirs(parent, svn_add, verbosity, pad)
    os.mkdir(dir)
    if not svn_add:
        return
    if os.system('svn info %r >/dev/null 2>&1' % parent) > 0:
        if verbosity > 1:
            print('%sNot part of a svn working copy; cannot add directory' % pad)
        return
    cmd = ['svn', 'add', dir]
    if verbosity > 1:
        print('%sRunning: %s' % (pad, ' '.join(cmd)))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if verbosity > 1 and stdout:
        print('Script output:')
        print(stdout)

def substitute_filename(fn, vars):
    for var, value in vars.items():
        fn = fn.replace('+%s+' % var, str(value))
    return fn

def substitute_content(content, vars, filename='<string>',
                       use_cheetah=False, template_renderer=None):
    global Cheetah
    v = standard_vars.copy()
    v.update(vars)
    vars = v
    if template_renderer is not None:
        return template_renderer(content, vars, filename=filename)
    if not use_cheetah:
        tmpl = LaxTemplate(content)
        try:
            return tmpl.substitute(TypeMapper(v))
        except Exception as e:
            _add_except(e, ' in file %s' % filename)
            raise
    if Cheetah is None:
        import Cheetah.Template
    tmpl = Cheetah.Template.Template(source=content,
                                     searchList=[vars])
    return careful_sub(tmpl, vars, filename)

def careful_sub(cheetah_template, vars, filename):
    """
    Substitutes the template with the variables, using the
    .body() method if it exists.  It assumes that the variables
    were also passed in via the searchList.
    """
    if not hasattr(cheetah_template, 'body'):
        return sub_catcher(filename, vars, str, cheetah_template)
    body = cheetah_template.body
    args, varargs, varkw, defaults = inspect.getargspec(body)
    call_vars = {}
    for arg in args:
        if arg in vars:
            call_vars[arg] = vars[arg]
    return sub_catcher(filename, vars, body, **call_vars)

def sub_catcher(filename, vars, func, *args, **kw):
    """
    Run a substitution, returning the value.  If an error occurs, show
    the filename.  If the error is a NameError, show the variables.
    """
    try:
        return func(*args, **kw)
    except SkipTemplate as e:
        print('Skipping file %s' % filename)
        if str(e):
            print(str(e))
        raise
    except Exception as e:
        print('Error in file %s:' % filename)
        if isinstance(e, NameError):
            for name, value in sorted(vars.items()):
                print('%s = %r' % (name, value))
        raise

def html_quote(s):
    if s is None:
        return ''
    return cgi.escape(str(s), 1)

def url_quote(s):
    if s is None:
        return ''
    return quote(str(s))

def test(conf, true_cond, false_cond=None):
    if conf:
        return true_cond
    else:
        return false_cond

def skip_template(condition=True, *args):
    """
    Raise SkipTemplate, which causes copydir to skip the template
    being processed.  If you pass in a condition, only raise if that
    condition is true (allows you to use this with string.Template)

    If you pass any additional arguments, they will be used to
    instantiate SkipTemplate (generally use like
    ``skip_template(license=='GPL', 'Skipping file; not using GPL')``)
    """
    if condition:
        raise SkipTemplate(*args)

def _add_except(exc, info):
    if not hasattr(exc, 'args') or exc.args is None:
        return
    args = list(exc.args)
    if args:
        args[0] += ' ' + info
    else:
        args = [info]
    exc.args = tuple(args)
    return


standard_vars = {
    'nothing': None,
    'html_quote': html_quote,
    'url_quote': url_quote,
    'empty': '""',
    'test': test,
    'repr': repr,
    'str': str,
    'bool': bool,
    'SkipTemplate': SkipTemplate,
    'skip_template': skip_template,
    }

class TypeMapper(dict):

    def __getitem__(self, item):
        options = item.split('|')
        for op in options[:-1]:
            try:
                value = eval_with_catch(op, dict(self.items()))
                break
            except (NameError, KeyError):
                pass
        else:
            value = eval(options[-1], dict(self.items()))
        if value is None:
            return ''
        else:
            return str(value)

def eval_with_catch(expr, vars):
    try:
        return eval(expr, vars)
    except Exception as e:
        _add_except(e, 'in expression %r' % expr)
        raise

class LaxTemplate(string.Template):
    # This change of pattern allows for anything in braces, but
    # only identifiers outside of braces:
    pattern = r"""
    \$(?:
      (?P<escaped>\$)             |   # Escape sequence of two delimiters
      (?P<named>[_a-z][_a-z0-9]*) |   # delimiter and a Python identifier
      {(?P<braced>.*?)}           |   # delimiter and a braced identifier
      (?P<invalid>)                   # Other ill-formed delimiter exprs
    )
    """
