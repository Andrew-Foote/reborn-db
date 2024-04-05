from slugify import slugify as _slugify

def slugify(x):
    x = x.translate({
        ord('♀'): 'F', ord('♂'): 'M',  # for nidorans
        ord('!'): '_emark_', ord('?'): '_qmark_', # for unowns and certain trainer anmes
    })

    return _slugify(x)