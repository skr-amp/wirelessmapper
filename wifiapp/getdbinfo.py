import sqlite3
import pymysql
from flask import jsonify
from wifiapp import app

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
    res = {"type": "FeatureCollection", "features": aplist}
    print(res)
    return jsonify(res)
