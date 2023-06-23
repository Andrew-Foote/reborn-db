# Purpose

Basically, this website is [pokemondb](https://pokemondb.net/), but for [Pokémon Reborn](https://www.rebornevo.com/pr/index.html/). It's a place where you can get information on Pokémon, moves, items, etc., where the information will be valid for Pokémon Reborn, even where Reborn differs from the official Pokémon games. It also contains Reborn-specific information on encounters, trainers, etc.

# Architecture

The website is based on an SQLite database, which is generated from files in the Pokémon Reborn installation using a bunch of Python scripts. A further bunch of Python scripts turn this SQLite database into a static website, which is stored in a separate [Git repository](https://github.com/Andrew-Foote/reborn-db-site) and served via [GitHub Pages](https://andrew-foote.github.io/reborn-db-site).

# Data download instructions

The SQLite database itself is not stored in this Git repository as largeish binary files make Git slow. However I've uploaded a recent copy (as of 2023-06-23) to Google Drive at [https://drive.google.com/file/d/18po9y19qKWbhLYRJQaLWtLl1hnvCeahJ/view?usp=sharing](https://drive.google.com/file/d/18po9y19qKWbhLYRJQaLWtLl1hnvCeahJ/view?usp=sharing), and hopefully I'll remember to update this copy as I update the database in future.

I use [DB Browser for SQLite](https://sqlitebrowser.org/) to browse the data most of the time, but there are some tables (e.g. `pokemon_encounter_rate`) which make use of a custom collation, and there are also custom functions that I've found useful for generating the website views. The custom collations and functions aren't stored with the database, so if you view it using DB Browser for SQLite, you can't use them. If you do want to use them, you can set up a virtual environment for the project according to the instructions below, then open up the Python shell within the virtual environment and do

    from reborndb import DB

Then you will be able to access a database connection object via the expression `DB.H`, which you can use to run SQL queries. See `reborndb\connection.py` for the interface of this connection object.

# Build instructions

Set the repository base directory as the current working directory:

     cd reborn-db

Create a virtual environment (replace `py` with whatever command you use to invoke Python):

     py -m venv env

Install modules from requirements.txt (replace `env\Scripts\pip` with `env\bin\pip` if on Mac/Linux):

     env\Scripts\pip install -r requirements.txt

Edit `reborndb/settings.py` and ensure that `REBORN_INSTALL_PATH` points to a Pokémon Reborn installation.

Build the database:

     env\Scripts\python __main__.py --full db

(Note: the first time you do this, you need to use the `--full` option. Afterwards, most of the time you can omit it; this will skip rebuilding parts of the database that are particularly time-consuming to rebuild.)

Build the website:

    env\Scripts\python __main__.py site

Run a HTTP server so you can access the website on localhost (port 8000):

    env\Scripts\python __main__.py serve

You can also combine arguments to `__main__.py` to do the last three steps in one command:

    env\Scripts\python __main__.py db site serve