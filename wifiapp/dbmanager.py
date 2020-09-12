import sqlite3
import pymysql

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




# try:
#     createdb('sqlite', 'mydb')
#     # createdb('mysql', 'mydb', dbhost='localhost', dbuser='root', dbpasswd='6170810088')
# except Exception as e:
#     print(e)