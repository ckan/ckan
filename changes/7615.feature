`validators` attribute of a declared config option makes an attempt to parse
argument to validators as python literals. If **all** arguments can be parsed,
they are passed to a validator factory with original types. If at least one
argument is not a valid python literal, all values are passed as a string(old
behavior). Space characters are still not allowed inside arguments, use `\\x20`
symbol if you need a space in literal::

    # Not changed
    `validators: v(xxx)` # v("xxx")
    `validators: v("xxx",yyy)` # v("xxx", "yyy")
    `validators: v(1,2,none)` # v("1", "2", "none")
    `validators: v("hello\\x20world")` # v("hello world")

    # Changed
    `validators: v("xxx")` # v("xxx")
    `validators: v("xxx",1)` # v("xxx", 1)
    `validators: v(1,2,None)` # v(1, 2, None)
