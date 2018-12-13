# -*- coding: iso-8859-15 -*-
"""IP4 address range set implementation.

Implements an IPv4-range type.

Copyright (C) 2006, Heiko Wundram.
Released under the MIT-license.
"""

# Version information
# -------------------

__author__ = "Heiko Wundram <me@modelnine.org>"
__version__ = "0.2"
__revision__ = "3"
__date__ = "2006-01-20"


# Imports
# -------

import intset
import socket


# IP4Range class
# --------------

class IP4Range(intset.IntSet):
    """IP4 address range class with efficient storage of address ranges.
    Supports all set operations."""

    _MINIP4 = 0
    _MAXIP4 = (1<<32) - 1
    _UNITYTRANS = "".join([chr(n) for n in range(256)])
    _IPREMOVE = "0123456789."

    def __init__(self,*args):
        """Initialize an ip4range class. The constructor accepts an unlimited
        number of arguments that may either be tuples in the form (start,stop),
        integers, longs or strings, where start and stop in a tuple may
        also be of the form integer, long or string.

        Passing an integer or long means passing an IPv4-address that's already
        been converted to integer notation, whereas passing a string specifies
        an address where this conversion still has to be done. A string
        address may be in the following formats:

        - 1.2.3.4    - a plain address, interpreted as a single address
        - 1.2.3      - a set of addresses, interpreted as 1.2.3.0-1.2.3.255
        - localhost  - hostname to look up, interpreted as single address
        - 1.2.3<->5  - a set of addresses, interpreted as 1.2.3.0-1.2.5.255
        - 1.2.0.0/16 - a set of addresses, interpreted as 1.2.0.0-1.2.255.255

        Only the first three notations are valid if you use a string address in
        a tuple, whereby notation 2 is interpreted as 1.2.3.0 if specified as
        lower bound and 1.2.3.255 if specified as upper bound, not as a range
        of addresses.

        Specifying a range is done with the <-> operator. This is necessary
        because '-' might be present in a hostname. '<->' shouldn't be, ever.
        """

        # Special case copy constructor.
        if len(args) == 1 and isinstance(args[0],IP4Range):
            super(IP4Range,self).__init__(args[0])
            return

        # Convert arguments to tuple syntax.
        args = list(args)
        for i in range(len(args)):
            argval = args[i]
            if isinstance(argval,str):
                if "<->" in argval:
                    # Type 4 address.
                    args[i] = self._parseRange(*argval.split("<->",1))
                    continue
                elif "/" in argval:
                    # Type 5 address.
                    args[i] = self._parseMask(*argval.split("/",1))
                else:
                    # Type 1, 2 or 3.
                    args[i] = self._parseAddrRange(argval)
            elif isinstance(argval,tuple):
                if len(tuple) <> 2:
                    raise ValueError("Tuple is of invalid length.")
                addr1, addr2 = argval
                if isinstance(addr1,str):
                    addr1 = self._parseAddrRange(addr1)[0]
                elif not isinstance(addr1,(int,long)):
                    raise TypeError("Invalid argument.")
                if isinstance(addr2,str):
                    addr2 = self._parseAddrRange(addr2)[1]
                elif not isinstance(addr2,(int,long)):
                    raise TypeError("Invalid argument.")
                args[i] = (addr1,addr2)
            elif not isinstance(argval,(int,long)):
                raise TypeError("Invalid argument.")

        # Initialize the integer set.
        super(IP4Range,self).__init__(min=self._MINIP4,max=self._MAXIP4,*args)

    # Parsing functions
    # -----------------

    def _parseRange(self,addr1,addr2):
        naddr1, naddr1len = _parseAddr(addr1)
        naddr2, naddr2len = _parseAddr(addr2)
        if naddr2len < naddr1len:
            naddr2 += naddr1&(((1<<((naddr1len-naddr2len)*8))-1)<<
                              (naddr2len*8))
            naddr2len = naddr1len
        elif naddr2len > naddr1len:
            raise ValueError("Range has more dots than address.")
        naddr1 <<= (4-naddr1len)*8
        naddr2 <<= (4-naddr2len)*8
        naddr2 += (1<<((4-naddr2len)*8))-1
        return (naddr1,naddr2)

    def _parseMask(self,addr,mask):
        naddr, naddrlen = _parseAddr(addr)
        naddr <<= (4-naddrlen)*8
        try:
            if not mask:
                masklen = 0
            else:
                masklen = int(mask)
            if not 0 <= masklen <= 32:
                raise ValueError
        except ValueError:
            try:
                mask = _parseAddr(mask,False)
            except ValueError:
                raise ValueError("Mask isn't parseable.")
            remaining = 0
            masklen = 0
            if not mask:
                masklen = 0
            else:
                while not (mask&1):
                    remaining += 1
                while (mask&1):
                    mask >>= 1
                    masklen += 1
                if remaining+masklen <> 32:
                    raise ValueError("Mask isn't a proper host mask.")
        naddr1 = naddr & (((1<<masklen)-1)<<(32-masklen))
        naddr2 = naddr1 + (1<<(32-masklen)) - 1
        return (naddr1,naddr2)

    def _parseAddrRange(self,addr):
        naddr, naddrlen = _parseAddr(addr)
        naddr1 = naddr<<((4-naddrlen)*8)
        naddr2 = ( (naddr<<((4-naddrlen)*8)) +
                   (1<<((4-naddrlen)*8)) - 1 )
        return (naddr1,naddr2)

    # Utility functions
    # -----------------

    def _int2ip(self,num):
        rv = []
        for i in range(4):
            rv.append(str(num&255))
            num >>= 8
        return ".".join(reversed(rv))

    # Iterating
    # ---------

    def iteraddresses(self):
        """Returns an iterator which iterates over ips in this iprange. An
        IP is returned in string form (e.g. '1.2.3.4')."""

        for v in super(IP4Range,self).__iter__():
            yield self._int2ip(v)

    def iterranges(self):
        """Returns an iterator which iterates over ip-ip ranges which build
        this iprange if combined. An ip-ip pair is returned in string form
        (e.g. '1.2.3.4-2.3.4.5')."""

        for r in self._ranges:
            if r[1]-r[0] == 1:
                yield self._int2ip(r[0])
            else:
                yield '%s-%s' % (self._int2ip(r[0]),self._int2ip(r[1]-1))

    def itermasks(self):
        """Returns an iterator which iterates over ip/mask pairs which build
        this iprange if combined. An IP/Mask pair is returned in string form
        (e.g. '1.2.3.0/24')."""

        for r in self._ranges:
            for v in self._itermasks(r):
                yield v

    def _itermasks(self,r):
        ranges = [r]
        while ranges:
            cur = ranges.pop()
            curmask = 0
            while True:
                curmasklen = 1<<(32-curmask)
                start = (cur[0]+curmasklen-1)&(((1<<curmask)-1)<<(32-curmask))
                if start >= cur[0] and start+curmasklen <= cur[1]:
                    break
                else:
                    curmask += 1
            yield "%s/%s" % (self._int2ip(start),curmask)
            if cur[0] < start:
                ranges.append((cur[0],start))
            if cur[1] > start+curmasklen:
                ranges.append((start+curmasklen,cur[1]))

    __iter__ = iteraddresses

    # Printing
    # --------

    def __repr__(self):
        """Returns a string which can be used to reconstruct this iprange."""

        rv = []
        for start, stop in self._ranges:
            if stop-start == 1:
                rv.append("%r" % (self._int2ip(start),))
            else:
                rv.append("(%r,%r)" % (self._int2ip(start),
                                       self._int2ip(stop-1)))
        return "%s(%s)" % (self.__class__.__name__,",".join(rv))

def _parseAddr(addr,lookup=True):
    if lookup and addr.translate(IP4Range._UNITYTRANS, IP4Range._IPREMOVE):
        try:
            addr = socket.gethostbyname(addr)
        except socket.error:
            raise ValueError("Invalid Hostname as argument.")
    naddr = 0
    for naddrpos, part in enumerate(addr.split(".")):
        if naddrpos >= 4:
            raise ValueError("Address contains more than four parts.")
        try:
            if not part:
                part = 0
            else:
                part = int(part)
            if not 0 <= part < 256:
                raise ValueError
        except ValueError:
            raise ValueError("Address part out of range.")
        naddr <<= 8
        naddr += part
    return naddr, naddrpos+1

def ip2int(addr, lookup=True):
    return _parseAddr(addr, lookup=lookup)[0]

if __name__ == "__main__":
    # Little test script.
    x = IP4Range("172.22.162.250/24")
    y = IP4Range("172.22.162.250","172.22.163.250","172.22.163.253<->255")
    print x
    for val in x.itermasks():
        print val
    for val in y.itermasks():
        print val
    for val in (x|y).itermasks():
        print val
    for val in (x^y).iterranges():
        print val
    for val in x:
        print val
