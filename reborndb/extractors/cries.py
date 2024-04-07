from reborndb import DB, settings

def extract() -> None:
    paths = (settings.REBORN_INSTALL_PATH / 'Audio/SE').glob('???Cry*.ogg')
    rows: list[tuple[str, bytes]] = []

    for path in paths:
        with path.open('rb') as f:
            content = f.read()
        
        rows.append((path.stem, content))

    with DB.H.transaction():
        DB.H.bulk_insert('cry', ('id', 'content'), rows)
