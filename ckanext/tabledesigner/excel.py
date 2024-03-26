import re

# also escape {} for safety when combined with .format
CONTROL_CHARACTERS = r'([\x00-\x1f\x7f-\x9f{}]+)'


def excel_literal(value: str) -> str:
    """
    return a quoted value safe for use in excel formulas
    """
    safe_unsafe = iter(re.split(CONTROL_CHARACTERS, value))
    out = ['"', next(safe_unsafe)]
    for unsafe in safe_unsafe:
        out.append('"&' + '&'.join(f'CHAR({ord(u)})' for u in unsafe) + '&"')
        out.append(next(safe_unsafe))
    out.append('"')
    return ''.join(out)
