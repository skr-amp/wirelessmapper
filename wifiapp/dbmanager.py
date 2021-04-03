import sqlite3
import pymysql
import os
from wifiapp import app
from flask import flash

def createdb(dbtype, dbname, dbdata):
    """function to create a new local sqlite or mysql database"""

    createsqlite = ("""CREATE TABLE ap (
    	                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
    	                    bssid VARCHAR(18), 
    	                    ssid VARCHAR(64), 
    	                    frequency INTEGER, 
    	                    capabilities VARCHAR(120), 
    	                    bestlat INTEGER, 
    	                    bestlon INTEGER, 
    	                    bestlevel INTEGER, 
    	                    vendor VARCHAR(120))""",
                   """CREATE TABLE device (
                          id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                          devicename VARCHAR(64) UNIQUE)""",
                   """CREATE TABLE location (
                          id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                          apid INTEGER, 
                          level INTEGER, 
                          lat INTEGER, 
                          lon INTEGER, 
                          altitude INTEGER, 
                          accuracy INTEGER, 
                          time DATETIME, 
                          deviceid INTEGER)""",
                  """CREATE TABLE apchange (
                          id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                          apid INTEGER, 
                          ssid VARCHAR(64), 
                          capabilities VARCHAR(120), 
                          time DATETIME)""",
                  """CREATE TABLE importfiles (
                          id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
                          filefeature INTEGER,
                          filesize INTEGER, 
                          filetype VARCHAR(6),
                          lastimportbssid VARCHAR(18),
                          checkloc INTEGER,
                          importaccuracy INTEGER,
                 	      importtime DATETIME)""")


    createmysql = ("""CREATE TABLE ap (
	                    id INTEGER NOT NULL AUTO_INCREMENT, 
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
	                    id INTEGER NOT NULL AUTO_INCREMENT, 
	                    devicename VARCHAR(64) UNIQUE, 
	                    PRIMARY KEY (id))""",
                 """CREATE TABLE location (
	                    id INTEGER NOT NULL AUTO_INCREMENT, 
	                    apid INTEGER, 
	                    level INTEGER, 
	                    lat FLOAT, 
	                    lon FLOAT, 
	                    altitude FLOAT, 
	                    accuracy FLOAT, 
	                    time DATETIME, 
	                    deviceid INTEGER, 
	                    PRIMARY KEY (id))""",
                 """CREATE TABLE apchange (
                   	    id INTEGER NOT NULL AUTO_INCREMENT, 
                   	    apid INTEGER, 
                   	    ssid VARCHAR(64), 
	                    frequency INTEGER, 
	                    capabilities VARCHAR(120), 
                   	    time DATETIME, 
                   	    PRIMARY KEY (id))""",
                 """CREATE TABLE importfiles (
                        id INTEGER NOT NULL AUTO_INCREMENT, 
                        filefeature INTEGER,
                        filesize INTEGER, 
                        filetype VARCHAR(6),
                        lastimportbssid VARCHAR(18),
                        checkloc INTEGER,
                        importaccuracy INTEGER,
                 	    importtime DATETIME, 
                        PRIMARY KEY (id))"""
                   )

    if dbexsist(dbtype=dbtype, dbname=dbname, dbhost=dbdata['dbhost'], dbuser=dbdata['dbuser'], dbpassword=dbdata['dbpassword']):
        if dbtype == "sqlite":
            flash("The database file already exists", "info")
        elif dbtype == "mysql":
            flash("The database already exists on the MySQL server", "info")
        adddb(dbtype=dbtype, dbname=dbname, dbhost=dbdata['dbhost'], dbuser=dbdata['dbuser'], dbpassword=dbdata['dbpassword'], dbdescription=dbdata['dbdescription'])
    else:
        if dbtype == 'sqlite':
            conn = sqlite3.connect('wifiapp/localdb/' + dbname)
            cursor = conn.cursor()
            for sql in createsqlite:
                cursor.execute(sql)
            conn.commit()
            conn.close()
        elif dbtype == 'mysql':
            conn = pymysql.connect(host=dbdata['dbhost'], user=dbdata['dbuser'], password=dbdata['dbpassword'])
            conn.cursor().execute('create database ' + dbname)
            conn.close()

            conn = pymysql.connect(host=dbdata['dbhost'], user=dbdata['dbuser'], password=dbdata['dbpassword'], db=dbname)
            for sql in createmysql:
                conn.cursor().execute(sql)
            conn.close()
        flash("Database created", "info")
        return adddb(dbtype=dbtype, dbname=dbname, dbhost=dbdata['dbhost'], dbuser=dbdata['dbuser'], dbpassword=dbdata['dbpassword'], dbdescription=dbdata['dbdescription'])


def adddb(dbtype, dbname, dbhost, dbuser, dbpassword, dbdescription):
    """Function for adding a record of a new database to the application database"""
    if not dbexsist(dbtype=dbtype, dbname=dbname, dbhost=dbhost, dbuser=dbuser, dbpassword=dbpassword):
        if dbtype == "sqlite":
            flash("There is no such database file", "error")
        elif dbtype == "mysql":
            flash("Such a database does not exist on the MySQL server", "error")
        return False
    if not dbvalidate(dbtype=dbtype, dbname=dbname, dbhost=dbhost, dbuser=dbuser, dbpassword=dbpassword):
        flash("Invalid format of the database being added", "error")
        return False
    if dbinappdb(dbtype=dbtype, dbname=dbname, dbhost=dbhost, dbuser=dbuser, dbpassword=dbpassword):
        flash("The database is already in the list", "info")
        return False
    if dbtype == "sqlite":
        sql = "INSERT INTO databases (type, dbname, description) VALUES('{}', '{}', '{}')".format(dbtype, dbname, dbdescription)
    elif dbtype == "mysql":
        sql = "INSERT INTO databases (type, dbname, host, user, password, description) VALUES('{}', '{}', '{}', '{}', '{}', '{}')".format(dbtype, dbname, dbhost, dbuser, dbpassword, dbdescription)
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    conn.close()
    flash("Database added.", "info")
    return True

def deldb(dbid):
    """Function for deleting a database from a mysql server or local database by its ID"""
    db = getdbinfo(dbid)
    if db[1] == "sqlite":
        os.remove(os.path.join('wifiapp/localdb/', db[2]))
        flash("Local database file deleted", "info")
    elif db[1] == "mysql":
        conn = pymysql.connect(host=db[3], user=db[4], password=db[5])
        conn.cursor().execute('DROP DATABASE IF EXISTS ' + db[2])
        conn.close()
        flash("Database deleted from the MySQL server", "info")

def delfromappdb(dbid):
    """Function to delete a database record from the application database by its ID"""
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute('DELETE FROM databases WHERE id=?', (dbid,))
    conn.commit()
    conn.close()
    flash("Database is removed from the list", "info")

def getdbinfo(dbid):
    """Function for getting information about the database from the application database by its ID"""
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM databases WHERE id=?', (dbid,))
    dbinfo = cursor.fetchone()
    conn.close()
    return dbinfo

def dbinappdb(dbtype, dbname, dbhost, dbuser, dbpassword):
    """Checking if there is a new database in the application database"""
    if dbtype == "sqlite":
        sql = "SELECT * FROM databases WHERE type='sqlite' AND dbname='{}'".format(dbname)
    elif dbtype == "mysql":
        sql = "SELECT * FROM databases WHERE type='mysql' AND dbname='{}' AND host='{}' AND user='{}' AND password='{}'".format(dbname, dbhost, dbuser, dbpassword)
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute(sql)
    res = True if cursor.fetchone() else False
    conn.close()
    return res

def dbvalidate(dbtype, dbname, dbhost, dbuser, dbpassword):
    """Function for checking the correctness of database tables and columns"""
    tables = []
    columns = []
    reqtables = {'ap', 'device', 'location', 'apchange', 'importfiles'}
    reqcolums = {'ap':{'id', 'bssid', 'ssid', 'frequency', 'capabilities', 'bestlat', 'bestlon', 'bestlevel', 'vendor'},
                 'device':{'id', 'devicename'},
                 'location':{'id', 'apid', 'level', 'lat', 'lon', 'altitude', 'accuracy', 'time', 'deviceid'},
                 'apchange':{'id', 'apid', 'ssid', 'capabilities'},
                 'importfiles':{'id', 'filefeature', 'filesize', 'filetype', 'importaccuracy', 'lastimportbssid', 'checkloc', 'importtime'}}
    if dbtype == "sqlite":
        conn = sqlite3.connect('wifiapp/localdb/' + dbname)
        cursor = conn.cursor()
        for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            tables.append(table[0])
    elif dbtype == "mysql":
        conn = pymysql.connect(host=dbhost, user=dbuser, password=dbpassword, db=dbname)
        cursor = conn.cursor()
        cursor.execute('SHOW TABLES')
        for table in cursor.fetchall():
            tables.append(table[0])
    conn.close()
    if not reqtables.issubset(set(tables)):
        return False

    for tab in reqtables:
        if dbtype == "sqlite":
            conn = sqlite3.connect('wifiapp/localdb/' + dbname)
            cursor = conn.cursor()
            cursor.execute("select * from %s" % tab)
            columns = list(map(lambda x: x[0], cursor.description))
        elif dbtype == "mysql":
            conn = pymysql.connect(host=dbhost, user=dbuser, password=dbpassword, db=dbname)
            cursor = conn.cursor()
            cursor.execute("DESCRIBE %s" % tab)
            columns = list(map(lambda x: x[0], cursor.fetchall()))
        conn.close()
        if not reqcolums[tab].issubset(set(columns)):
            return False
    return True

def dbexsist(dbtype, dbname, **dbdata):
    if dbtype == "sqlite":
        return sqliteexist('wifiapp/localdb/' + dbname)
    elif dbtype == "mysql":
        return mysqlexist(dbname, dbdata['dbhost'], dbdata['dbuser'], dbdata['dbpassword'])


def mysqlsrvexist(host, user, password):
    try:
        conn = pymysql.connect(host=host, user=user, password=password)
    except:
        flash("Access denied to MySQL server. Check authorization data: host, username and password." , "error")
        return False
    else:
        conn.close()
        return True


def dblist():
    res = []
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    for db in cursor.execute('SELECT * FROM databases'):
        exsist = dbexsist(dbtype=db[1], dbname=db[2], dbhost=db[3], dbuser=db[4], dbpassword=db[5])
        res.append({'id':db[0], 'dbname':db[2], 'type':db[1], 'host':'local database' if db[3] == None else db[3], 'user':db[4], 'password':db[5],
                    'numberofap':db[6], 'numberofloc':db[7], 'timefirst':db[8], 'timelast':db[9], 'description':db[10], 'dbexsist':exsist})
    conn.close()
    return res

def setdb(dbid):
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM databases WHERE id=?', (dbid,))
    dbinfo = cursor.fetchone()
    exsist = dbexsist(dbtype=dbinfo[1], dbname=dbinfo[2], dbhost=dbinfo[3], dbuser=dbinfo[4], dbpassword=dbinfo[5])

    if exsist:
        cursor.execute('UPDATE config SET option_value=? WHERE option_name="currentdbid"', (dbid,))
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
