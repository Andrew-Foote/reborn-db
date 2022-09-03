# Purpose

Basically, this website is [pokemondb](https://pokemondb.net/), but for [Pokémon Reborn](https://www.rebornevo.com/pr/index.html/). It's a place where you can get information on Pokémon, moves, items, etc., where the information will be valid for Pokémon Reborn, where Reborn differs from the official Pokémon games. It also contains Reborn-specific information on encounters, trainers, etc.

# Architecture

The website is based on an SQLite database, which is generated from files in the Pokémon Reborn installation using a bunch of Python scripts. A further bunch of Python scripts turn this SQLite database into a static website, which is then copied into my [GitHub Pages repository](https://github.com/Andrew-Foote/Andrew-Foote.github.io) and thus made available at [https://andrew-foote.github.io/reborn-db](https://andrew-foote.github.io/reborn-db).

# Build instructions

Set the repository base directory as the current working directory:

     cd reborn-db

Create a virtual environment (replace `py` with whatever command you use to invoke Python):

     py -m venv env

Install modules from requirements.txt (replace `env\Scripts\pip` with `env\bin\pip` if on Mac/Linux):

     env\Scripts\pip install -r requirements.txt
     
Edit `reborndb/settings.py` and ensure that `REBORN_INSTALL_PATH` points to a Pokémon Reborn installation.

Build the database:

     env\Scripts\python __main__.py db

Build the website:

    env\Scripts\python __main__.py site

Run a HTTP server so you can access the website on localhost (port 8000):

    env\Scripts\python __main__.py serve

You can also combine arguments to `__main__.py` to do the last three steps in one command:

    env\Scripts\python __main__.py db site serve