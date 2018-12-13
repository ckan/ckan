# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This is a module to check the filesystem for the presence and
permissions of certain files.  It can also be used to correct the
permissions (but not existance) of those files.

Currently only supports Posix systems (with Posixy permissions).
Permission stuff can probably be stubbed out later.
"""
import os

def read_perm_spec(spec):
    """
    Reads a spec like 'rw-r--r--' into a octal number suitable for
    chmod.  That is characters in groups of three -- first group is
    user, second for group, third for other (all other people).  The
    characters are r (read), w (write), and x (executable), though the
    executable can also be s (sticky).  Files in sticky directories
    get the directories permission setting.

    Examples::

      >>> print oct(read_perm_spec('rw-r--r--'))
      0o644
      >>> print oct(read_perm_spec('rw-rwsr--'))
      0o2664
      >>> print oct(read_perm_spec('r-xr--r--'))
      0o544
      >>> print oct(read_perm_spec('r--------'))
      0o400
    """
    total_mask = 0
    # suid/sgid modes give this mask in user, group, other mode:
    set_bits = (0o4000, 0o2000, 0)
    pieces = (spec[0:3], spec[3:6], spec[6:9])
    for i, (mode, set_bit) in enumerate(zip(pieces, set_bits)):
        mask = 0
        read, write, exe = list(mode)
        if read == 'r':
            mask = mask | 4
        elif read != '-':
            raise ValueError(
                "Character %r unexpected (should be '-' or 'r')"
                % read)
        if write == 'w':
            mask = mask | 2
        elif write != '-':
            raise ValueError(
                "Character %r unexpected (should be '-' or 'w')"
                % write)
        if exe == 'x':
            mask = mask | 1
        elif exe not in ('s', '-'):
            raise ValueError(
                "Character %r unexpected (should be '-', 'x', or 's')"
                % exe)
        if exe == 's' and i == 2:
            raise ValueError((
                "The 'other' executable setting cannot be suid/sgid ('s')"))
        mask = mask << ((2-i)*3)
        if exe == 's':
            mask = mask | set_bit
        total_mask = total_mask | mask
    return total_mask

modes = [
    (0o4000, 'setuid bit',
     'setuid bit: make contents owned by directory owner'),
    (0o2000, 'setgid bit',
     'setgid bit: make contents inherit permissions from directory'),
    (0o1000, 'sticky bit',
     'sticky bit: append-only directory'),
    (0o0400, 'read by owner', 'read by owner'),
    (0o0200, 'write by owner', 'write by owner'),
    (0o0100, 'execute by owner', 'owner can search directory'),
    (0o0040, 'allow read by group members',
     'allow read by group members',),
    (0o0020, 'allow write by group members',
     'allow write by group members'),
    (0o0010, 'execute by group members',
     'group members can search directory'),
    (0o0004, 'read by others', 'read by others'),
    (0o0002, 'write by others', 'write by others'),
    (0o0001, 'execution by others', 'others can search directory'),
    ]

exe_bits = [0o100, 0o010, 0o001]
exe_mask = 0o111
full_mask = 0o7777

def mode_diff(filename, mode, **kw):
    """
    Returns the differences calculated using ``calc_mode_diff``
    """
    cur_mode = os.stat(filename).st_mode
    return calc_mode_diff(cur_mode, mode, **kw)

def calc_mode_diff(cur_mode, mode, keep_exe=True,
                   not_set='not set: ',
                   set='set: '):
    """
    Gives the difference between the actual mode of the file and the
    given mode.  If ``keep_exe`` is true, then if the mode doesn't
    include any executable information the executable information will
    simply be ignored.  High bits are also always ignored (except
    suid/sgid and sticky bit).

    Returns a list of differences (empty list if no differences)
    """
    for exe_bit in exe_bits:
        if mode & exe_bit:
            keep_exe = False
    diffs = []
    isdir = os.path.isdir(filename)
    for bit, file_desc, dir_desc in modes:
        if keep_exe and bit in exe_bits:
            continue
        if isdir:
            desc = dir_desc
        else:
            desc = file_desc
        if (mode & bit) and not (cur_mode & bit):
            diffs.append(not_set + desc)
        if not (mode & bit) and (cur_mode & bit):
            diffs.append(set + desc)
    return diffs

def calc_set_mode(cur_mode, mode, keep_exe=True):
    """
    Calculates the new mode given the current node ``cur_mode`` and
    the mode spec ``mode`` and if ``keep_exe`` is true then also keep
    the executable bits in ``cur_mode`` if ``mode`` has no executable
    bits in it.  Return the new mode.

    Examples::

      >>> print oct(calc_set_mode(0o775, 0o644))
      0o755
      >>> print oct(calc_set_mode(0o775, 0o744))
      0o744
      >>> print oct(calc_set_mode(0o10600, 0o644))
      0o10644
      >>> print oct(calc_set_mode(0o775, 0o644, False))
      0o644
    """
    for exe_bit in exe_bits:
        if mode & exe_bit:
            keep_exe = False
    # This zeros-out full_mask parts of the current mode:
    keep_parts = (cur_mode | full_mask) ^ full_mask
    if keep_exe:
        keep_parts = keep_parts | (cur_mode & exe_mask)
    new_mode = keep_parts | mode
    return new_mode

def set_mode(filename, mode, **kw):
    """
    Sets the mode on ``filename`` using ``calc_set_mode``
    """
    cur_mode = os.stat(filename).st_mode
    new_mode = calc_set_mode(cur_mode, mode, **kw)
    os.chmod(filename, new_mode)

def calc_ownership_spec(spec):
    """
    Calculates what a string spec means, returning (uid, username,
    gid, groupname), where there can be None values meaning no
    preference.

    The spec is a string like ``owner:group``.  It may use numbers
    instead of user/group names.  It may leave out ``:group``.  It may
    use '-' to mean any-user/any-group.

    """
    import grp
    import pwd
    user = group = None
    uid = gid = None
    if ':' in spec:
        user_spec, group_spec = spec.split(':', 1)
    else:
        user_spec, group_spec = spec, '-'
    if user_spec == '-':
        user_spec = '0'
    if group_spec == '-':
        group_spec = '0'
    try:
        uid = int(user_spec)
    except ValueError:
        uid = pwd.getpwnam(user_spec)
        user = user_spec
    else:
        if not uid:
            uid = user = None
        else:
            user = pwd.getpwuid(uid).pw_name
    try:
        gid = int(group_spec)
    except ValueError:
        gid = grp.getgrnam(group_spec)
        group = group_spec
    else:
        if not gid:
            gid = group = None
        else:
            group = grp.getgrgid(gid).gr_name
    return (uid, user, gid, group)

def ownership_diff(filename, spec):
    """
    Return a list of differences between the ownership of ``filename``
    and the spec given.
    """
    import grp
    import pwd
    diffs = []
    uid, user, gid, group = calc_ownership_spec(spec)
    st = os.stat(filename)
    if uid and uid != st.st_uid:
        diffs.append('owned by %s (should be %s)' %
                     (pwd.getpwuid(st.st_uid).pw_name, user))
    if gid and gid != st.st_gid:
        diffs.append('group %s (should be %s)' %
                     (grp.getgrgid(st.st_gid).gr_name, group))
    return diffs

def set_ownership(filename, spec):
    """
    Set the ownership of ``filename`` given the spec.
    """
    uid, user, gid, group = calc_ownership_spec(spec)
    st = os.stat(filename)
    if not uid:
        uid = st.st_uid
    if not gid:
        gid = st.st_gid
    os.chmod(filename, uid, gid)

class PermissionSpec(object):
    """
    Represents a set of specifications for permissions.

    Typically reads from a file that looks like this::

      rwxrwxrwx user:group filename

    If the filename ends in /, then it expected to be a directory, and
    the directory is made executable automatically, and the contents
    of the directory are given the same permission (recursively).  By
    default the executable bit on files is left as-is, unless the
    permissions specifically say it should be on in some way.

    You can use 'nomodify filename' for permissions to say that any
    permission is okay, and permissions should not be changed.

    Use 'noexist filename' to say that a specific file should not
    exist.

    Use 'symlink filename symlinked_to' to assert a symlink destination

    The entire file is read, and most specific rules are used for each
    file (i.e., a rule for a subdirectory overrides the rule for a
    superdirectory).  Order does not matter.
    """

    def __init__(self):
        self.paths = {}

    def parsefile(self, filename):
        f = open(filename)
        lines = f.readlines()
        f.close()
        self.parselines(lines, filename=filename)

    commands = {}

    def parselines(self, lines, filename=None):
        for lineindex, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            command = parts[0]
            if command in self.commands:
                cmd = self.commands[command](*parts[1:])
            else:
                cmd = self.commands['*'](*parts)
            self.paths[cmd.path] = cmd

    def check(self):
        action = _Check(self)
        self.traverse(action)

    def fix(self):
        action = _Fixer(self)
        self.traverse(action)

    def traverse(self, action):
        paths = self.paths_sorted()
        checked = {}
        for path, checker in list(paths)[::-1]:
            self.check_tree(action, path, paths, checked)
        for path, checker in paths:
            if path not in checked:
                action.noexists(path, checker)

    def traverse_tree(self, action, path, paths, checked):
        if path in checked:
            return
        self.traverse_path(action, path, paths, checked)
        if os.path.isdir(path):
            for fn in os.listdir(path):
                fn = os.path.join(path, fn)
                self.traverse_tree(action, fn, paths, checked)

    def traverse_path(self, action, path, paths, checked):
        checked[path] = None
        for check_path, checker in paths:
            if path.startswith(check_path):
                action.check(check_path, checker)
                if not checker.inherit:
                    break

    def paths_sorted(self):
        paths = sorted(self.paths.items(),
                       key=lambda key_value: len(key_value[0]),
                       reversed=True)

class _Rule(object):
    class __metaclass__(type):
        def __new__(meta, class_name, bases, d):
            cls = type.__new__(meta, class_name, bases, d)
            PermissionSpec.commands[cls.__name__] = cls
            return cls

    inherit = False
    def noexists(self):
        return ['Path %s does not exist' % path]

class _NoModify(_Rule):

    name = 'nomodify'

    def __init__(self, path):
        self.path = path

    def fix(self, path):
        pass

class _NoExist(_Rule):

    name = 'noexist'

    def __init__(self, path):
        self.path = path

    def check(self, path):
        return ['Path %s should not exist' % path]

    def noexists(self, path):
        return []

    def fix(self, path):
        # @@: Should delete?
        pass

class _SymLink(_Rule):

    name = 'symlink'
    inherit = True

    def __init__(self, path, dest):
        self.path = path
        self.dest = dest

    def check(self, path):
        assert path == self.path, (
            "_Symlink should only be passed specific path %s (not %s)"
            % (self.path, path))
        try:
            link = os.path.readlink(path)
        except OSError as e:
            if e.errno != 22:
                raise
            return ['Path %s is not a symlink (should point to %s)'
                    % (path, self.dest)]
        if link != self.dest:
            return ['Path %s should symlink to %s, not %s'
                    % (path, self.dest, link)]
        return []

    def fix(self, path):
        assert path == self.path, (
            "_Symlink should only be passed specific path %s (not %s)"
            % (self.path, path))
        if not os.path.exists(path):
            os.symlink(path, self.dest)
        else:
            # @@: This should correct the symlink or something:
            print('Not symlinking %s' % path)

class _Permission(_Rule):

    name = '*'

    def __init__(self, perm, owner, dir):
        self.perm_spec = read_perm_spec(perm)
        self.owner = owner
        self.dir = dir

    def check(self, path):
        return mode_diff(path, self.perm_spec)

    def fix(self, path):
        set_mode(path, self.perm_spec)

class _Strategy(object):

    def __init__(self, spec):
        self.spec = spec

class _Check(_Strategy):

    def noexists(self, path, checker):
        checker.noexists(path)

    def check(self, path, checker):
        checker.check(path)

class _Fixer(_Strategy):

    def noexists(self, path, checker):
        pass

    def check(self, path, checker):
        checker.fix(path)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

