from pathlib import Path
import shutil
from reborndb import DB, settings

def extract_dir(dirname: str, tablename: str) -> None:
    with DB.H.transaction():
        DB.H.bulk_insert(
            tablename,
            ['name'],
            [
                (path.stem,) for path
                in (settings.REBORN_INSTALL_PATH / 'Audio' / dirname).iterdir()
            ]
        )

def extract() -> None:
    extract_dir('BGM', 'background_music')
    extract_dir('BGS', 'background_sound')
    extract_dir('ME', 'music_effect')
    extract_dir('SE', 'sound_effect')
    site_audio_path = Path('reborn-db-site/audio')

    if not site_audio_path.exists():
        print('Copying audio files from Reborn installation...')
        site_audio_path.mkdir()
        reborn_audio_path = settings.REBORN_INSTALL_PATH / 'Audio'
        shutil.copytree(reborn_audio_path / 'BGM', site_audio_path / 'bgm')
        shutil.copytree(reborn_audio_path / 'BGS', site_audio_path / 'bgs')
        shutil.copytree(reborn_audio_path / 'ME', site_audio_path / 'me')
        shutil.copytree(reborn_audio_path / 'SE', site_audio_path / 'se')