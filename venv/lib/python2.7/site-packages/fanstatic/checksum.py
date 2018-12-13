import os
import hashlib
from datetime import datetime

VCS_NAMES = ['.svn', '.git', '.bzr', '.hg']
IGNORED_EXTENSIONS = ['.swp', '.tmp', '.pyc', '.pyo']


def list_directory(path, include_directories=True):
    # Skip over any VCS directories.
    for root, dirs, files in os.walk(path):
        for dir in VCS_NAMES:
            try:
                dirs.remove(dir)
            except ValueError:
                pass
        # We are also interested in the directories.
        if include_directories:
            yield os.path.join(root)
        for file in files:
            _, ext = os.path.splitext(file)
            if ext in IGNORED_EXTENSIONS:
                continue
            yield os.path.join(root, file)


def mtime(path):
    latest = 0
    for path in list_directory(path):
        mtime = os.path.getmtime(path)
        latest = max(mtime, latest)
    return datetime.fromtimestamp(latest).isoformat()[:22]

def md5(path):
    chcksm = hashlib.md5()
    for path in list_directory(path, include_directories=False):
        chcksm.update(path)
        try:
            f = open(path, 'rb')
            while True:
                # 256kb chunks.
                # XXX how to optimize chunk size?
                chunk = f.read(0x40000)
                if not chunk:
                    break
                chcksm.update(chunk)
        finally:
            f.close()
    return chcksm.hexdigest()
