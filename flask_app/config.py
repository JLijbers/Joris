import os


FLASK_APP_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(FLASK_APP_DIR)

# Configuration constants
CONFIG_PATH = os.path.join(FLASK_APP_DIR, 'config.ini')
STATIC_PATH = os.path.join(FLASK_APP_DIR, 'static')
TEMPLATE_PATH = os.path.join(FLASK_APP_DIR, 'templates')
DATABASE_PATH = os.path.join(FLASK_APP_DIR, 'db')
IGNORE_PATH = os.path.join(FLASK_APP_DIR, 'ignore.json')
