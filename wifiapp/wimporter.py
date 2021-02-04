import csv
import datetime
import os
import sqlite3
import pymysql
from wifiapp import app

def csv_info_read(filename):
    """Getting information about a csv file"""
    target = os.path.join(app.config['APP_ROOT'], 'upload/')
    path = "/".join([target, filename])
    f_csv = open(path, "r", encoding="UTF8")
    csv_data = csv.reader(f_csv, delimiter=',', quotechar='"')
    firststr = next(csv_data)
    csv_info = {}
    if firststr[0][:9] == "WigleWifi":
        csv_info["app"] = firststr[0]
        csv_info["device"] = firststr[2][6:]
        next(csv_data)
        firsttime = next(csv_data)[3]
        loc = 0
        for line in csv_data:
            endtime = line[3]
            if line[10] == "WIFI": loc += 1

        csv_info["time"] = firsttime + " - " + endtime
        csv_info["location"] = loc
        csv_info["uploadtime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        csv_info["app"] = "UNKNOWN"
        csv_info["device"] = "UNKNOWN"
    return csv_info

def get_devices():
    """Getting a dictionary of devices stored in the database"""
    devices = {}
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        for device in cursor.execute('SELECT * FROM device'):
            devices[device[1]] = device[0]
        conn.close()
    elif app.config['CURRENT_DB_TYPE'] == 'mysql':
        conn = pymysql.connect(host=app.config['CURRENT_DB_HOST'], user=app.config['CURRENT_DB_USER'], password=app.config['CURRENT_DB_PASS'], db=app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM device')
        for device in cursor.fetchall():
            devices[device[1]] = device[0]
        conn.close()
    return devices

def add_device_db(device):
    """Adding a new device to the database"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO 'device' ('devicename') VALUES(?)", (device,))
        conn.commit()
        conn.close()
    elif app.config['CURRENT_DB_TYPE'] == 'mysql':
        conn = pymysql.connect(host=app.config['CURRENT_DB_HOST'], user=app.config['CURRENT_DB_USER'], password=app.config['CURRENT_DB_PASS'], db=app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO device (devicename) VALUES (%s)", (device,))
        conn.commit()
        conn.close()
    return True