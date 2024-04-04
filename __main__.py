# The entry point. All scripts are run from here to ensure that imports work properly.

import os
import sys
from scripts import refresh_database, create_views, regenerate_site, run_server

SCRIPTS = (refresh_database, create_views, regenerate_site, run_server)

SHORT_NAMES = {
	'db': 'refresh_database',
	'views': 'create_views',
	'site': 'regenerate_site',
	'serve': 'run_server'
}

SCRIPTS_DICT = {script.__name__: script for script in SCRIPTS}

if len(sys.argv) <= 1:
	print('no actions specified (list as arguments)')
	print('available actions:')

	for script in SCRIPTS:
		print(f'  {script.__name__}')

actions = sys.argv[1:]

for action in actions:
	if action.startswith('--'):
		print(f'setting {action[2:]}')
		os.environ[action[2:]] = '1'
		continue

for action in actions:
	if action in SHORT_NAMES:
		action = SHORT_NAMES[action]
		SCRIPTS_DICT[f'scripts.{action}'].run()
