from __future__ import with_statement

from os import path

try:
    import json
except ImportError:
    import simplejson as json

PERSISTENCE_FILENAME="persisted_state.json"

class PersistentState(object):
    """Base class for the serialisation of the state of the harvest. Stores itself as JSON at the filepath given in the init phase."""
    def __init__(self, filepath=None, filename=PERSISTENCE_FILENAME, create = True):
        self.state = {}
        self.filepath = None
        if filepath:
            self.set_filepath(filepath, filename, create)
        self.revert()
    
    def set_filepath(self, filepath, filename=PERSISTENCE_FILENAME, create = True):
        if path.isdir(filepath):
            # print "Filepath exists - setting persistence file to %s" % path.join(filepath, filename)
            self.filepath = path.join(filepath, filename)
            if create and not path.isfile(self.filepath):
                self.sync()
            return True
        else:
            print "Filepath does not exist - persistence file would not be able to be created"
            return False
    
    def revert(self):
        """Revert the state to the version stored on disc."""
        if self.filepath:
            if path.isfile(self.filepath):
                serialised_file = open(self.filepath, "r")
                try:
                    self.state = json.load(serialised_file)
                except ValueError:
                    print "No JSON information could be read from the persistence file - could be empty: %s" % self.filepath
                    self.state = {}
                finally:
                    serialised_file.close()
            else:
                print "The persistence file has not yet been created or does not exist, so the state cannot be read from it yet."
        else:
            print "Filepath to the persistence file is not set. State cannot be read."
            return False
    
    def sync(self):
        """Synchronise and update the stored state to the in-memory state."""
        if self.filepath:
            serialised_file = open(self.filepath, "w")
            json.dump(self.state, serialised_file)
            serialised_file.close()
        else:
            print "Filepath to the persistence file is not set. State cannot be synced to disc."

    # Dictionary methods
    def keys(self): return self.state.keys()
    def has_key(self, key): return self.state.has_key(key)
    def items(self): return self.state.items()
    def values(self): return self.state.values()
    def clear(self): self.state.clear()
    def update(self, kw):
        for key in kw:
            self.state[key] = kw[key]
    def __setitem__(self, key, item): self.state[key] = item
    def __getitem__(self, key):
        try:
            return self.state[key]
        except KeyError:
            raise KeyError(key)
    def __repr__(self): return repr(self.state)
    def __cmp__(self, dict):
        if isinstance(dict, PersistentState):
            return cmp(self.state, dict.state)
        else:
            return cmp(self.state, dict)
    def __len__(self): return len(self.state)
    def __delitem__(self, key): del self.state[key]

