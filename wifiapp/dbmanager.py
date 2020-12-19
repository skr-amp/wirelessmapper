import sqlite3
import pymysql
import os
from wifiapp import app

def createdb(dbtype, dbname, **dbdata):
    """function to create a new local sqlite or mysql database"""
    createsql = ("""CREATE TABLE ap (
	                    id INTEGER NOT NULL, 
	                    bssid VARCHAR(18), 
	                    ssid VARCHAR(64), 
	                    frequency INTEGER, 
	                    capabilities VARCHAR(120), 
	                    bestlat FLOAT, 
	                    bestlon FLOAT, 
	                    bestlevel INTEGER, 
	                    vendor VARCHAR(120), 
	                    PRIMARY KEY (id))""",
	             """CREATE TABLE device (
	                    id INTEGER NOT NULL, 
	                    devicename VARCHAR(64), 
	                    PRIMARY KEY (id))""",
                 """CREATE TABLE location (
	                    id INTEGER NOT NULL, 
	                    apid INTEGER, 
	                    level INTEGER, 
	                    lat FLOAT, 
	                    lon FLOAT, 
	                    altitude FLOAT, 
	                    accuracy FLOAT, 
	                    time DATETIME, 
	                    deviceid INTEGER, 
	                    PRIMARY KEY (id))""")

    if dbtype == 'sqlite':
        conn = sqlite3.connect('localdb/' + dbname)
        cursor = conn.cursor()
        for sql in createsql:
            cursor.execute(sql)
        conn.commit()
        conn.close()
    elif dbtype == 'mysql':
        conn = pymysql.connect(host=dbdata['dbhost'], user=dbdata['dbuser'], password=dbdata['dbpasswd'])
        conn.cursor().execute('create database ' + dbname)
        conn.close()

        conn = pymysql.connect(host=dbdata['dbhost'], user=dbdata['dbuser'], password=dbdata['dbpasswd'], db=dbname)
        for sql in createsql:
            conn.cursor().execute(sql)
        conn.close()

def dblist():
    res = []
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    for db in cursor.execute('SELECT * FROM databases'):
        if db[1] == 'sqlite':
            dbexsist = sqliteexist('wifiapp/localdb/' + db[2])
        elif db[1] == 'mysql':
            dbexsist = mysqlexist(db[2], db[3], db[4], db[5])
        res.append({'id':db[0], 'dbname':db[2], 'type':db[1], 'host':'local database' if db[3] == None else db[3], 'user':db[4], 'password':db[5],
                    'numberofap':db[6], 'numberofloc':db[7], 'timefirst':db[8], 'timelast':db[9], 'description':db[10], 'dbexsist':dbexsist})
    conn.close()
    return res

def setdb(dbid):
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM databases WHERE id=?', dbid)
    dbinfo = cursor.fetchone()
    if dbinfo[1] == 'sqlite':
        dbexsist = sqliteexist('wifiapp/localdb/' + dbinfo[2])
    elif dbinfo[1] == 'mysql':
        dbexsist = mysqlexist(dbinfo[2], dbinfo[3], dbinfo[4], dbinfo[5])

    if dbexsist:
        cursor.execute('UPDATE config SET option_value=? WHERE option_name="currentdbid"', dbid)
        conn.commit()
        app.config['CURRENT_DB_ID'] = dbid
        app.config['CURRENT_DB_TYPE'] = dbinfo[1]
        app.config['CURRENT_DB_NAME'] = dbinfo[2]
        app.config['CURRENT_DB_HOST'] = dbinfo[3]
        app.config['CURRENT_DB_USER'] = dbinfo[4]
        app.config['CURRENT_DB_PASS'] = dbinfo[5]
    conn.close()

def sqliteexist(filename):
    from os.path import isfile, getsize
    if not isfile(filename):
        return False
    if getsize(filename) < 100: # SQLite database file header is 100 bytes
        return False
    with open(filename, 'rb') as fd:
        header = fd.read(100)
    return header[:16] == b'SQLite format 3\x00'

def mysqlexist(dbname, dbhost, dbuser, dbpass):
    try:
        conn = pymysql.connect(host=dbhost, user=dbuser, password=dbpass)
    except:
        return False
    cursor = conn.cursor()
    cursor.execute('SHOW DATABASES')
    dblist = cursor.fetchall()
    conn.close()
    return (dbname,) in dblist

def editdbinfo(dbid, host, user, password, description):
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    if host != None:
        cursor.execute('UPDATE databases SET host=? WHERE id=?',(host, dbid))
    if user != None:
        cursor.execute('UPDATE databases SET user=? WHERE id=?', (user, dbid))
    if password != None:
        cursor.execute('UPDATE databases SET password=? WHERE id=?', (password, dbid))
    cursor.execute('UPDATE databases SET description=? WHERE id=?',(description, dbid))
    conn.commit()
    conn.close()
