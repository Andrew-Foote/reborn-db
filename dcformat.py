from collections.abc import Mapping, Iterable
from dataclasses import is_dataclass, fields

def pretty_print(obj, indent=4):
    """
    Pretty prints a (possibly deeply-nested) dataclass.
    Each new block will be indented by `indent` spaces (default is 4).
    """
    print(stringify(obj, indent))

def stringify(obj, indent=4, _indents=0, parent_ids=()):
    if (
        isinstance(obj, (str, bytes))
        or (
            not isinstance(obj, (Mapping, Iterable))
            and not is_dataclass(obj)
        )
    ):
        return repr(obj)

    obj_id = id(obj)

    #if obj_id in parent_ids:
        #return f'<cycle to {obj_id}>'

    parent_ids = (*parent_ids, obj_id)        

    this_indent = indent * _indents * ' '
    next_indent = indent * (_indents + 1) * ' '
    start, end = f'{type(obj).__name__}(', ')'  # dicts, lists, and tuples will re-assign this

    if is_dataclass(obj):
        body = '\n'.join(
            f'{next_indent}{field.name}='
            f'{stringify(getattr(obj, field.name), indent, _indents + 1, parent_ids)},' for field in fields(obj)
        )

    elif isinstance(obj, Mapping):
        if isinstance(obj, dict):
            start, end = '{}'

        body = '\n'.join(
            f'{next_indent}{stringify(key, indent, _indents + 1, parent_ids)}: '
            f'{stringify(value, indent, _indents + 1, parent_ids)},' for key, value in obj.items()
        )

    else:  # is Iterable
        if isinstance(obj, list):
            start, end = '[]'
        elif isinstance(obj, tuple):
            start = '('

        body = '\n'.join(
            f'{next_indent}{stringify(item, indent, _indents + 1, parent_ids)},' for item in obj
        )

    return f'{start}\n{body}\n{this_indent}{end}'

