"""Small helpers for the words of a message."""
import re as _re


def a_(name):
    """NAME with its article, as said aloud: `a Length_T`, `an Area_T`,
    `a Euro_T`, `a Unit_T`."""
    n = str(name)
    vowel = _re.match(r"[AEIOUaeiou]", n) and not _re.match(r"(?i)(eu|uni|use|usa|usd|usu|ur[aeiou]|one\b|once)", n)
    return f"{'an' if vowel else 'a'} {n}"
