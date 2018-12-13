# -*- coding: iso-8859-15 -*-
"""Immutable integer set type.

Integer set class.

Copyright (C) 2006, Heiko Wundram.
Released under the MIT license.
"""

# Version information
# -------------------

__author__ = "Heiko Wundram <me@modelnine.org>"
__version__ = "0.2"
__revision__ = "6"
__date__ = "2006-01-20"


# Utility classes
# ---------------

class _Infinity(object):
    """Internal type used to represent infinity values."""

    __slots__ = ["_neg"]

    def __init__(self,neg):
        self._neg = neg

    def __lt__(self,value):
        if not isinstance(value,(int,long,_Infinity)):
            return NotImplemented
        return ( self._neg and
                 not ( isinstance(value,_Infinity) and value._neg ) )

    def __le__(self,value):
        if not isinstance(value,(int,long,_Infinity)):
            return NotImplemented
        return self._neg

    def __gt__(self,value):
        if not isinstance(value,(int,long,_Infinity)):
            return NotImplemented
        return not ( self._neg or
                     ( isinstance(value,_Infinity) and not value._neg ) )

    def __ge__(self,value):
        if not isinstance(value,(int,long,_Infinity)):
            return NotImplemented
        return not self._neg

    def __eq__(self,value):
        if not isinstance(value,(int,long,_Infinity)):
            return NotImplemented
        return isinstance(value,_Infinity) and self._neg == value._neg

    def __ne__(self,value):
        if not isinstance(value,(int,long,_Infinity)):
            return NotImplemented
        return not isinstance(value,_Infinity) or self._neg <> value._neg

    def __repr__(self):
        return "None"


# Constants
# ---------

_MININF = _Infinity(True)
_MAXINF = _Infinity(False)


# Integer set class
# -----------------

class IntSet(object):
    """Integer set class with efficient storage in a RLE format of ranges.
    Supports minus and plus infinity in the range."""

    __slots__ = ["_ranges","_min","_max","_hash"]

    def __init__(self,*args,**kwargs):
        """Initialize an integer set. The constructor accepts an unlimited
        number of arguments that may either be tuples in the form of
        (start,stop) where either start or stop may be a number or None to
        represent maximum/minimum in that direction. The range specified by
        (start,stop) is always inclusive (differing from the builtin range
        operator).

        Keyword arguments that can be passed to an integer set are min and
        max, which specify the minimum and maximum number in the set,
        respectively. You can also pass None here to represent minus or plus
        infinity, which is also the default.
        """

        # Special case copy constructor.
        if len(args) == 1 and isinstance(args[0],IntSet):
            if kwargs:
                raise ValueError("No keyword arguments for copy constructor.")
            self._min = args[0]._min
            self._max = args[0]._max
            self._ranges = args[0]._ranges
            self._hash = args[0]._hash
            return

        # Initialize set.
        self._ranges = []

        # Process keyword arguments.
        self._min = kwargs.pop("min",_MININF)
        self._max = kwargs.pop("max",_MAXINF)
        if self._min is None:
            self._min = _MININF
        if self._max is None:
            self._max = _MAXINF

        # Check keyword arguments.
        if kwargs:
            raise ValueError("Invalid keyword argument.")
        if not ( isinstance(self._min,(int,long)) or self._min is _MININF ):
            raise TypeError("Invalid type of min argument.")
        if not ( isinstance(self._max,(int,long)) or self._max is _MAXINF ):
            raise TypeError("Invalid type of max argument.")
        if ( self._min is not _MININF and self._max is not _MAXINF and
             self._min > self._max ):
            raise ValueError("Minimum is not smaller than maximum.")
        if isinstance(self._max,(int,long)):
            self._max += 1

        # Process arguments.
        for arg in args:
            if isinstance(arg,(int,long)):
                start, stop = arg, arg+1
            elif isinstance(arg,tuple):
                if len(arg) <> 2:
                    raise ValueError("Invalid tuple, must be (start,stop).")

                # Process argument.
                start, stop = arg
                if start is None:
                    start = self._min
                if stop is None:
                    stop = self._max

                # Check arguments.
                if not ( isinstance(start,(int,long)) or start is _MININF ):
                    raise TypeError("Invalid type of tuple start.")
                if not ( isinstance(stop,(int,long)) or stop is _MAXINF ):
                    raise TypeError("Invalid type of tuple stop.")
                if ( start is not _MININF and stop is not _MAXINF and
                     start > stop ):
                    continue
                if isinstance(stop,(int,long)):
                    stop += 1
            else:
                raise TypeError("Invalid argument.")

            if start > self._max:
                continue
            elif start < self._min:
                start = self._min
            if stop < self._min:
                continue
            elif stop > self._max:
                stop = self._max
            self._ranges.append((start,stop))

        # Normalize set.
        self._normalize()

    # Utility functions for set operations
    # ------------------------------------

    def _iterranges(self,r1,r2,minval=_MININF,maxval=_MAXINF):
        curval = minval
        curstates = {"r1":False,"r2":False}
        imax, jmax = 2*len(r1), 2*len(r2)
        i, j = 0, 0
        while i < imax or j < jmax:
            if i < imax and ( ( j < jmax and
                                r1[i>>1][i&1] < r2[j>>1][j&1] ) or
                              j == jmax ):
                cur_r, newname, newstate = r1[i>>1][i&1], "r1", not (i&1)
                i += 1
            else:
                cur_r, newname, newstate = r2[j>>1][j&1], "r2", not (j&1)
                j += 1
            if curval < cur_r:
                if cur_r > maxval:
                    break
                yield curstates, (curval,cur_r)
                curval = cur_r
            curstates[newname] = newstate
        if curval < maxval:
            yield curstates, (curval,maxval)

    def _normalize(self):
        self._ranges.sort()
        i = 1
        while i < len(self._ranges):
            if self._ranges[i][0] < self._ranges[i-1][1]:
                self._ranges[i-1] = (self._ranges[i-1][0],
                                     max(self._ranges[i-1][1],
                                         self._ranges[i][1]))
                del self._ranges[i]
            else:
                i += 1
        self._ranges = tuple(self._ranges)
        self._hash = hash(self._ranges)

    def __coerce__(self,other):
        if isinstance(other,IntSet):
            return self, other
        elif isinstance(other,(int,long,tuple)):
            try:
                return self, self.__class__(other)
            except TypeError:
                # Catch a type error, in that case the structure specified by
                # other is something we can't coerce, return NotImplemented.
                # ValueErrors are not caught, they signal that the data was
                # invalid for the constructor. This is appropriate to signal
                # as a ValueError to the caller.
                return NotImplemented
        elif isinstance(other,list):
            try:
                return self, self.__class__(*other)
            except TypeError:
                # See above.
                return NotImplemented
        return NotImplemented

    # Set function definitions
    # ------------------------

    def _make_function(name,type,doc,pall,pany=None):
        """Makes a function to match two ranges. Accepts two types: either
        'set', which defines a function which returns a set with all ranges
        matching pall (pany is ignored), or 'bool', which returns True if pall
        matches for all ranges and pany matches for any one range. doc is the
        dostring to give this function. pany may be none to ignore the any
        match.

        The predicates get a dict with two keys, 'r1', 'r2', which denote
        whether the current range is present in range1 (self) and/or range2
        (other) or none of the two, respectively."""

        if type == "set":
            def f(self,other):
                coerced = self.__coerce__(other)
                if coerced is NotImplemented:
                    return NotImplemented
                other = coerced[1]
                newset = self.__class__.__new__(self.__class__)
                newset._min = min(self._min,other._min)
                newset._max = max(self._max,other._max)
                newset._ranges = []
                for states, (start,stop) in \
                        self._iterranges(self._ranges,other._ranges,
                                         newset._min,newset._max):
                    if pall(states):
                        if newset._ranges and newset._ranges[-1][1] == start:
                            newset._ranges[-1] = (newset._ranges[-1][0],stop)
                        else:
                            newset._ranges.append((start,stop))
                newset._ranges = tuple(newset._ranges)
                newset._hash = hash(self._ranges)
                return newset
        elif type == "bool":
            def f(self,other):
                coerced = self.__coerce__(other)
                if coerced is NotImplemented:
                    return NotImplemented
                other = coerced[1]
                _min = min(self._min,other._min)
                _max = max(self._max,other._max)
                found = not pany
                for states, (start,stop) in \
                        self._iterranges(self._ranges,other._ranges,_min,_max):
                    if not pall(states):
                        return False
                    found = found or pany(states)
                return found
        else:
            raise ValueError("Invalid type of function to create.")
        try:
            f.func_name = name
        except TypeError:
            pass
        f.func_doc = doc
        return f

    # Intersection.
    __and__ = _make_function("__and__","set",
                             "Intersection of two sets as a new set.",
                             lambda s: s["r1"] and s["r2"])
    __rand__ = _make_function("__rand__","set",
                              "Intersection of two sets as a new set.",
                              lambda s: s["r1"] and s["r2"])
    intersection = _make_function("intersection","set",
                                  "Intersection of two sets as a new set.",
                                  lambda s: s["r1"] and s["r2"])

    # Union.
    __or__ = _make_function("__or__","set",
                            "Union of two sets as a new set.",
                            lambda s: s["r1"] or s["r2"])
    __ror__ = _make_function("__ror__","set",
                             "Union of two sets as a new set.",
                             lambda s: s["r1"] or s["r2"])
    union = _make_function("union","set",
                           "Union of two sets as a new set.",
                           lambda s: s["r1"] or s["r2"])

    # Difference.
    __sub__ = _make_function("__sub__","set",
                             "Difference of two sets as a new set.",
                             lambda s: s["r1"] and not s["r2"])
    __rsub__ = _make_function("__rsub__","set",
                              "Difference of two sets as a new set.",
                              lambda s: s["r2"] and not s["r1"])
    difference = _make_function("difference","set",
                                "Difference of two sets as a new set.",
                                lambda s: s["r1"] and not s["r2"])

    # Symmetric difference.
    __xor__ = _make_function("__xor__","set",
                             "Symmetric difference of two sets as a new set.",
                             lambda s: s["r1"] ^ s["r2"])
    __rxor__ = _make_function("__rxor__","set",
                              "Symmetric difference of two sets as a new set.",
                              lambda s: s["r1"] ^ s["r2"])
    symmetric_difference = _make_function("symmetric_difference","set",
                                          "Symmetric difference of two sets as a new set.",
                                          lambda s: s["r1"] ^ s["r2"])

    # Containership testing.
    __contains__ = _make_function("__contains__","bool",
                                  "Returns true if self is superset of other.",
                                  lambda s: s["r1"] or not s["r2"])
    issubset = _make_function("issubset","bool",
                              "Returns true if self is subset of other.",
                              lambda s: s["r2"] or not s["r1"])
    istruesubset = _make_function("istruesubset","bool",
                                  "Returns true if self is true subset of other.",
                                  lambda s: s["r2"] or not s["r1"],
                                  lambda s: s["r2"] and not s["r1"])
    issuperset = _make_function("issuperset","bool",
                                "Returns true if self is superset of other.",
                                lambda s: s["r1"] or not s["r2"])
    istruesuperset = _make_function("istruesuperset","bool",
                                    "Returns true if self is true superset of other.",
                                    lambda s: s["r1"] or not s["r2"],
                                    lambda s: s["r1"] and not s["r2"])
    overlaps = _make_function("overlaps","bool",
                              "Returns true if self overlaps with other.",
                              lambda s: True,
                              lambda s: s["r1"] and s["r2"])

    # Comparison.
    __eq__ = _make_function("__eq__","bool",
                            "Returns true if self is equal to other.",
                            lambda s: not ( s["r1"] ^ s["r2"] ))
    __ne__ = _make_function("__ne__","bool",
                            "Returns true if self is different to other.",
                            lambda s: True,
                            lambda s: s["r1"] ^ s["r2"])

    # Clean up namespace.
    del _make_function

    # Define other functions.
    def inverse(self):
        """Inverse of set as a new set."""

        newset = self.__class__.__new__(self.__class__)
        newset._min = self._min
        newset._max = self._max
        newset._ranges = []
        laststop = self._min
        for r in self._ranges:
            if laststop < r[0]:
                newset._ranges.append((laststop,r[0]))
                laststop = r[1]
        if laststop < self._max:
            newset._ranges.append((laststop,self._max))
        return newset

    __invert__ = inverse

    # Hashing
    # -------

    def __hash__(self):
        """Returns a hash value representing this integer set. As the set is
        always stored normalized, the hash value is guaranteed to match for
        matching ranges."""

        return self._hash

    # Iterating
    # ---------

    def __len__(self):
        """Get length of this integer set. In case the length is larger than
        2**31 (including infinitely sized integer sets), it raises an
        OverflowError. This is due to len() restricting the size to
        0 <= len < 2**31."""

        if not self._ranges:
            return 0
        if self._ranges[0][0] is _MININF or self._ranges[-1][1] is _MAXINF:
            raise OverflowError("Infinitely sized integer set.")
        rlen = 0
        for r in self._ranges:
            rlen += r[1]-r[0]
        if rlen >= 2**31:
            raise OverflowError("Integer set bigger than 2**31.")
        return rlen

    def len(self):
        """Returns the length of this integer set as an integer. In case the
        length is infinite, returns -1. This function exists because of a
        limitation of the builtin len() function which expects values in
        the range 0 <= len < 2**31. Use this function in case your integer
        set might be larger."""

        if not self._ranges:
            return 0
        if self._ranges[0][0] is _MININF or self._ranges[-1][1] is _MAXINF:
            return -1
        rlen = 0
        for r in self._ranges:
            rlen += r[1]-r[0]
        return rlen

    def __nonzero__(self):
        """Returns true if this integer set contains at least one item."""

        return bool(self._ranges)

    def __iter__(self):
        """Iterate over all values in this integer set. Iteration always starts
        by iterating from lowest to highest over the ranges that are bounded.
        After processing these, all ranges that are unbounded (maximum 2) are
        yielded intermixed."""

        ubranges = []
        for r in self._ranges:
            if r[0] is _MININF:
                if r[1] is _MAXINF:
                    ubranges.extend(([0,1],[-1,-1]))
                else:
                    ubranges.append([r[1]-1,-1])
            elif r[1] is _MAXINF:
                ubranges.append([r[0],1])
            else:
                for val in xrange(r[0],r[1]):
                    yield val
        if ubranges:
            while True:
                for ubrange in ubranges:
                    yield ubrange[0]
                    ubrange[0] += ubrange[1]

    # Printing
    # --------

    def __repr__(self):
        """Return a representation of this integer set. The representation is
        executable to get an equal integer set."""

        rv = []
        for start, stop in self._ranges:
            if ( isinstance(start,(int,long)) and isinstance(stop,(int,long))
                 and stop-start == 1 ):
                rv.append("%r" % start)
            elif isinstance(stop,(int,long)):
                rv.append("(%r,%r)" % (start,stop-1))
            else:
                rv.append("(%r,%r)" % (start,stop))
        if self._min is not _MININF:
            rv.append("min=%r" % self._min)
        if self._max is not _MAXINF:
            rv.append("max=%r" % self._max)
        return "%s(%s)" % (self.__class__.__name__,",".join(rv))

if __name__ == "__main__":
    # Little test script demonstrating functionality.
    x = IntSet((10,20),30)
    y = IntSet((10,20))
    z = IntSet((10,20),30,(15,19),min=0,max=40)
    print x
    print x&110
    print x|110
    print x^(15,25)
    print x-12
    print 12 in x
    print x.issubset(x)
    print y.issubset(x)
    print x.istruesubset(x)
    print y.istruesubset(x)
    for val in x:
        print val
    print x.inverse()
    print x == z
    print x == y
    print x <> y
    print hash(x)
    print hash(z)
    print len(x)
    print x.len()
