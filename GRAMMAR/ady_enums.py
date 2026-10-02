"""Enum members with values: `type Look_T is enum PLAIN = 0, KEYWORD = 1, ...`.

Either every member has a value or none does -- a reader never has to work out what
an unwritten one is. The values give the order: strictly ascending, and `ord`, `<` and
`case` follow them. Where they are consecutive (1, 2, 3 or 0, 1, 2) the enum is as
good as any other; where they are not (0, 2, 5) Nim refuses an array indexed by it,
a `for` over it, and `succ` and `pred`, so Adascript refuses them on both backends.

The backends read members from the parse tree with `member`, hand what they found to
`checked`, and ask `has_gaps` where a gap matters.
"""


def member(node):
    """(name, value) of an enum_member node; the value is None for a bare member."""
    inner = getattr(node, "nodes", None)
    if inner is not None and len(inner) == 3:          # NAME = INTEGER
        return str(inner[0].node), int(str(inner[2].node))
    return str(node.node), None


def checked(type_name, members):
    """MEMBERS, a list of (name, value-or-None), after refusing a mix of valued and
    bare members and values that do not ascend."""
    valued = [m for m in members if m[1] is not None]
    if valued and len(valued) != len(members):
        bare = next(name for name, value in members if value is None)
        raise SyntaxError(
            f"enum {type_name}: either every member has a value or none does; "
            f"{bare} has none")
    for (a, x), (b, y) in zip(valued, valued[1:]):
        if y <= x:
            raise SyntaxError(
                f"enum {type_name}: the values give the order, so they must ascend: "
                f"{b} = {y} comes after {a} = {x}")
    return members


def has_gaps(members):
    """Do the values skip a number? Bare members never do."""
    values = [v for _, v in members if v is not None]
    return any(y != x + 1 for x, y in zip(values, values[1:]))


def gaps_in_text(rhs):
    """Does the declaration text `enum A = 0, B = 2` have values that skip a number?"""
    import re
    values = [int(v) for v in re.findall(r"=\s*(\d+)", rhs)]
    return any(y != x + 1 for x, y in zip(values, values[1:]))


def refuse(type_name, what):
    """The refusal for an enum whose values skip a number, WHAT being asked of it."""
    raise SyntaxError(
        f"enum {type_name}: its values skip a number, so it cannot be {what}; "
        f"give consecutive values, or use a case or a dict")


def refuse_if_gapped_type(type_name, info, what):
    """Refuse WHAT of the enum TYPE_NAME if its registration INFO (tick_types) says its
    values skip a number."""
    if info and info.get("gapped"):
        refuse(type_name, what)


def refuse_if_gapped_value(expr, what):
    """Refuse WHAT of EXPR if it is a plain name of a variable whose type is an enum with
    gaps in its values (succ and pred of one have no meaning)."""
    from hek_parsec import ParserState
    sym = ParserState.symbol_table.lookup(expr) if expr.isidentifier() else None
    typ = ((sym.get("type") or "") if isinstance(sym, dict) else "")
    refuse_if_gapped_type(typ, getattr(ParserState, "tick_types", {}).get(typ), what)
