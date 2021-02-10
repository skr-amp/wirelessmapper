import csv
import datetime
import os
import sqlite3
import pymysql
import gzip
from wifiapp import app
from wifiapp.macvendor import GetVendor

import time

def csv_info_read(filename):
    """Getting information about a csv file"""
    csv.field_size_limit(500000)
    target = os.path.join(app.config['APP_ROOT'], 'upload/')
    path = "/".join([target, filename])
    extension = filename.rsplit('.', 1)[1]
    if extension == "gz":
        f_csv = gzip.open(path, 'rt', encoding="UTF8")
    elif extension == "csv":
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
        return False
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

def wigle_csv_import(app, socketio, filename, accuracy, deviceid):
    """"""
    with app.app_context():
        target = os.path.join(app.config['APP_ROOT'], 'upload/')
        path = "/".join([target, filename])
        extension = filename.rsplit('.', 1)[1]
        if extension == "gz":
            f_csv = gzip.open(path, 'rt', encoding="UTF8")
        elif extension == "csv":
            f_csv = open(path, "r", encoding="UTF8")
        csv_data = csv.reader(f_csv, delimiter=',', quotechar='"')
        next(csv_data)
        time.sleep(1)
        aplist = {}
        numberloc = 0
        numberap = 0
        for line in csv_data:
            bssid = line[0]
            ssid = line[1]
            capabilities = line[2]
            loctime = line[3]
            channel = line[4]
            loclevel = line[5]
            loclat = line[6]
            loclon = line[7]
            localtitude = line[8]
            locaccuracy = line[9]
            if line[10] == "WIFI" and float(locaccuracy) < float(accuracy):
                numberloc += 1
                if len(aplist) == 0 or not bssid in aplist.keys():
                    aplist[bssid] = {"ssid":ssid, "capabilities":capabilities, "frequency":channel_to_freq(channel), "location":[{"time":loctime, "level":loclevel, "lat":loclat, "lon":loclon, "altitude":localtitude, "accuracy":locaccuracy}, ]}
                    numberap += 1
                else:
                    aplist[bssid]["location"].append({"time":loctime, "level":loclevel, "lat":loclat, "lon":loclon, "altitude":localtitude, "accuracy":locaccuracy})
        socketio.send({"msg": "number_of_loc_and_ap", "numberloc":numberloc, "numberap":numberap}, broadcast=True)

        addedap = 0
        addedloc = 0
        checkloc =0
        for bssid in aplist.keys():
            apid = get_apid_in_db(bssid)
            msg = {"msg": "importinfo"}
            if len(apid) == 1:      #if the database already has only one access point with this bssid
                numberaddloc = add_loc_in_db(apid[0], aplist[bssid]["location"], deviceid)
                addedloc += numberaddloc
                calc_ap_coord(apid[0])
                msg["info"] = 'The access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} is already in the database. {2} new locations imported'.format(bssid, aplist[bssid]["ssid"], numberaddloc, apid[0])
            elif len(apid) > 1:     #if the database already has multiple access points with this bssid             !!!!!!!!!!!!!!!!!!!!!!!
                print("More than one access point with such bssid in the database: " + bssid)
            else:                   #there are no access points with this bssid in the database
                id = add_ap_in_db({"bssid":bssid, "ssid":aplist[bssid]["ssid"], "capabilities":aplist[bssid]["capabilities"], "frequency":aplist[bssid]["frequency"] })
                addedap += 1
                numberaddloc = add_loc_in_db(id, aplist[bssid]["location"], deviceid)
                addedloc += numberaddloc
                calc_ap_coord(id)
                msg["info"] = 'A new access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} has been added to the database. {2} new locations imported'.format(
                    bssid, aplist[bssid]["ssid"], numberaddloc, id)
            checkloc += len(aplist[bssid]["location"])
            msg["checkloc"] = checkloc
            socketio.send(msg, broadcast=True)
        msg = {"msg": "resultinfo"}
        msg["info"] = 'Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
        socketio.send(msg, broadcast=True)


def channel_to_freq(channel):
    """function returns the   frequency corresponding to the channel"""
    freqdict = {'1': 2412, '2': 2417, '3': 2422, '4': 2427, '5': 2432, '6': 2437, '7': 2442, '8': 2447, '9': 2452,
                '10': 2457, '11': 2462, '12': 2467, '13': 2472, '14': 2484,
                '34': 5170, '36': 5180, '38': 5190, '40': 5200, '42': 5210, '44': 5220, '46': 5230, '48': 5240,
                '50': 5250, '52': 5260, '54': 5270, '56': 5280, '58': 5290, '60': 5300, '62': 5310, '64': 5320,
                '100': 5500, '104': 5520, '108': 5540, '112': 5560, '116': 5580, '120': 5600, '124': 5620, '128': 5640,
                '132': 5660, '136': 5680, '140': 5700, '147': 5735, '149': 5745, '150': 5755, '152': 5760, '153': 5765,
                '155': 5775, '157': 5785, '159': 5795, '160': 5800, '161': 5805, '163': 5815, '165': 5825, '167': 5835,
                '171': 5855, '173': 5865, '177': 5885, '180': 5905}
    return freqdict[channel]

def get_apid_in_db(bssid):
    """Returns a list of access point IDs stored in the database with the specified bssid"""
    ids = []
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        for id in cursor.execute("SELECT id FROM ap WHERE bssid=?", (bssid,)):
            ids.append(id[0])
        conn.close()
    #elif app.config['CURRENT_DB_TYPE'] == 'mysql':

    return ids

def add_ap_in_db(ap):
    """adds a new access point to the database and returns its id"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ap ('bssid', 'ssid', 'frequency', 'capabilities', 'vendor') VALUES(?, ?, ?, ?, ?)",
                       (ap["bssid"], ap["ssid"], ap["frequency"], ap["capabilities"], GetVendor(ap["bssid"])))
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ROWID()")
        apid = cursor.fetchone()
        conn.close()
    #elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return apid[0]

def add_loc_in_db(apid, locations, deviceid):
    """adds locations to the database and returns the number of added locations"""
    locaddcount = 0
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        locindb = []
        for loc in cursor.execute("SELECT time, deviceid FROM location WHERE apid=?", (apid, )):
            locindb.append(loc)
        for location in locations:
            if not (location["time"], deviceid) in locindb:
                cursor.execute("INSERT INTO location ('apid', 'level', 'lat', 'lon', 'altitude', 'accuracy', 'time', 'deviceid') VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                               (apid, location["level"], location["lat"], location["lon"], location["altitude"], location["accuracy"], location["time"], deviceid))
                conn.commit()
                locaddcount += 1
        conn.close()
    #elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return locaddcount

def calc_ap_coord(apid):
    """"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT lat, lon, level FROM location WHERE apid=? AND level = (SELECT MAX(level) FROM location WHERE apid=?)", (apid, apid))
        res = cursor.fetchone()
        bestlat = res[0]
        bestlon = res[1]
        bestlevel = res[2]
        cursor.execute("UPDATE ap SET bestlat = ?, bestlon = ?, bestlevel = ?  WHERE id = ?",(bestlat, bestlon, bestlevel, apid))
        conn.commit()
        conn.close()
    #elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return True