`toolkit.asbool` now converts any iterable other than `list` and `tuple` into a `list`: `list(value)`.
Before, such values were just wrapped into a list, i.e: `[value]`
