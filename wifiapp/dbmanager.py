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
        res.append({'id':db[0], 'dbname':db[2], 'type':db[1], 'host':'locale database' if db[3] == None else db[3], 'numberofap':db[6], 'numberofloc':db[7], 'timefirst':db[8], 'timelast':db[9], 'description':db[10]})
    conn.close()
    return res

def setdb(dbid):
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute('UPDATE config SET option_value=? WHERE option_name="currentdbid"', dbid)
    conn.commit()

    cursor.execute('SELECT * FROM databases WHERE id=?', dbid)
    dbinfo = cursor.fetchone()
    app.config['CURRENT_DB_ID'] = dbid
    app.config['CURRENT_DB_TYPE'] = dbinfo[1]
    app.config['CURRENT_DB_NAME'] = dbinfo[2]
    app.config['CURRENT_DB_HOST'] = dbinfo[3]
    app.config['CURRENT_DB_USER'] = dbinfo[4]
    app.config['CURRENT_DB_PASS'] = dbinfo[5]

    conn.close()
#try:
#    createdb('sqlite', 'mydb')
#
#except Exception as e:
#    print(e)

