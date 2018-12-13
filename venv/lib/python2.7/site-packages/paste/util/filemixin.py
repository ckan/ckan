# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

class FileMixin(object):

    """
    Used to provide auxiliary methods to objects simulating files.
    Objects must implement write, and read if they are input files.
    Also they should implement close.

    Other methods you may wish to override:
    * flush()
    * seek(offset[, whence])
    * tell()
    * truncate([size])

    Attributes you may wish to provide:
    * closed
    * encoding (you should also respect that in write())
    * mode
    * newlines (hard to support)
    * softspace
    """

    def flush(self):
        pass

    def next(self):
        return self.readline()

    def readline(self, size=None):
        # @@: This is a lame implementation; but a buffer would probably
        # be necessary for a better implementation
        output = []
        while 1:
            next = self.read(1)
            if not next:
                return ''.join(output)
            output.append(next)
            if size and size > 0 and len(output) >= size:
                return ''.join(output)
            if next == '\n':
                # @@: also \r?
                return ''.join(output)

    def xreadlines(self):
        return self

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    
