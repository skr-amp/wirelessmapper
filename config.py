import os
import sqlite3

class Config(object):
    APP_ROOT = os.path.abspath(os.path.dirname(__file__))

    conn = sqlite3.connect('appdb.db')
    cur = conn.cursor()
    cur.execute('SELECT option_value FROM config WHERE option_name="currentdbid"')
    CURRENT_DB_ID = cur.fetchone()[0]
    cur.execute('SELECT * FROM databases WHERE id=?', (CURRENT_DB_ID,))
    dbinfo = cur.fetchone()
    conn.close()
    CURRENT_DB_TYPE = dbinfo[1]
    CURRENT_DB_NAME = dbinfo[2]
    CURRENT_DB_HOST = dbinfo[3]
    CURRENT_DB_USER = dbinfo[4]
    CURRENT_DB_PASS = dbinfo[5]


