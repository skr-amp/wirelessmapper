import sqlite3
import pymysql
from flask import jsonify
from wifiapp import app

def freqToChannel(freq):
    chdict = {2412: 1, 2417: 2, 2422: 3, 2427: 4, 2432: 5, 2437: 6, 2442: 7, 2447: 8, 2452: 9, 2457: 10, 2462: 11, 2467: 12, 2472: 13, 2484: 14}
    return chdict[int(freq)]


def apmarkers(bounds):
    boundslist = bounds.split(",")  #
    minlat = float(boundslist[1])  #
    maxlat = float(boundslist[3])  # получение границ отображения точек доступа
    minlon = float(boundslist[0])  #
    maxlon = float(boundslist[2])  #
    aplist = []

    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        for ap in cursor.execute('SELECT * FROM ap WHERE bestlat BETWEEN ? AND ? AND bestlon BETWEEN ? AND ?', (minlat, maxlat, minlon, maxlon)):
            aplist.append({"type": "Feature", "id": ap[0], "properties": {"ssid": ap[2], "bssid": ap[1]},
                           "geometry": {"type": "Point", "coordinates": [ap[6], ap[5]]}})
        conn.close()
    elif app.config['CURRENT_DB_TYPE'] == 'mysql':
        conn = pymysql.connect(host=app.config['CURRENT_DB_HOST'], user=app.config['CURRENT_DB_USER'], password=app.config['CURRENT_DB_PASS'], db=app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ap WHERE bestlat BETWEEN %s AND %s AND bestlon BETWEEN %s AND %s', (minlat, maxlat, minlon, maxlon))
        for ap in cursor.fetchall():
            aplist.append({"type": "Feature", "id": ap[0], "properties": {"ssid": ap[2], "bssid": ap[1]},
                           "geometry": {"type": "Point", "coordinates": [ap[6], ap[5]]}})
        conn.close()
    res = {"type": "FeatureCollection", "features": aplist}
    return jsonify(res)


def apinfo(apid):
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ap WHERE id=?', (apid,))
        apinfo = cursor.fetchone()

        channel = freqToChannel(apinfo[3])

        cursor.execute('SELECT MIN(time) FROM location WHERE apid=?', (apid,))
        firsttime = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(time) FROM location WHERE apid=?', (apid,))
        lasttime = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(level) FROM location WHERE apid=?', (apid,))
        bestlevel = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM location WHERE apid=?', (apid,))
        numberofloc = cursor.fetchone()[0]

        conn.close()

    elif app.config['CURRENT_DB_TYPE'] == 'mysql':
        conn = pymysql.connect(host=app.config['CURRENT_DB_HOST'], user=app.config['CURRENT_DB_USER'],
                               password=app.config['CURRENT_DB_PASS'], db=app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ap WHERE id=%s', apid)
        apinfo = cursor.fetchone()

        channel = freqToChannel(apinfo[3])

        cursor.execute('SELECT MIN(time) FROM location WHERE apid=%s', apid)
        firsttime = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(time) FROM location WHERE apid=%s', apid)
        lasttime = cursor.fetchone()[0]

        cursor.execute('SELECT MAX(level) FROM location WHERE apid=%s', apid)
        bestlevel = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM location WHERE apid=%s', apid)
        numberofloc = cursor.fetchone()[0]
        conn.close()

    res = {"ssid": apinfo[2], "bssid": apinfo[1], "capabilities": apinfo[4], "channel": channel,
           "vendor": apinfo[8], "bestlevel": bestlevel, "firsttime": firsttime, "lasttime": lasttime,
           "numberofloc": numberofloc}
    return jsonify(res)
