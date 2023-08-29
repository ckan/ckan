`toolkit.aslist` now converts any iterable other than ``list`` and `tuple` into a ``list``: ``list(value)``.
Before, such values were just wrapped into a list, i.e: ``[value]``.

.. list-table:: Short overview of changes
   :widths: 40 30 30
   :header-rows: 1

   * - Expresion
     - Before
     - After
   * - ``aslist([1,2])``
     - ``[1, 2]``
     - ``[1, 2]``
   * - ``aslist({1,2})``
     - ``[{1, 2}]``
     - ``[1, 2]``
   * - ``aslist({1: "one", 2: "two"})``
     - ``[{1: "one", 2: "two"}]``
     - ``[1, 2]``
   * - ``aslist(range(1,3))``
     - ``[range(1, 3)]``
     - ``[1, 2]``
