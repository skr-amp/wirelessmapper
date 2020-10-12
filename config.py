import os


class Config(object):
    APP_ROOT = os.path.abspath(os.path.dirname(__file__))
    CURRENT_DB = 'sqlite'
    CURRENT_DB_NAME = 'db.db'

