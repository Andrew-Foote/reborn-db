from slugify import slugify as _slugify

def slugify(x):
    # for nidorans
    x = x.translate({ord('♀'): 'F', ord('♂'): 'M'})

    # for unown forms
    if x == '!':
        return 'EMARK'
    elif x == '?':
        return 'QMARK'

    return _slugify(x)