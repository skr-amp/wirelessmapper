import csv
import time
import os
import sqlite3
import pymysql
import gzip
import pathlib
from wifiapp import app
from wifiapp.macvendor import GetVendor


def check_file(filename):
    """Getting information about a imported file"""
    fileinfo = {}
    target = os.path.join(app.config['APP_ROOT'], 'upload/')
    path = "/".join([target, filename])
    extension = pathlib.Path(path).suffixes

    # Check extension
    if extension[0] == ".csv":
        fileinfo["type"] = "csv"
        if len(extension) > 1 and extension[1] == ".gz":
            f_csv = gzip.open(path, 'rt', encoding="latin-1")
        else:
            f_csv = open(path, "r", encoding="latin-1")
    elif extension[0] == ".sqlite":
        fileinfo["type"] = "sqlite"

    # Check application
    if fileinfo["type"] == "csv":
        csv_data = csv.reader((line.replace('\0', '') for line in f_csv), delimiter=',', quotechar='"')
        firststr = next(csv_data)
        if firststr[0][:9] == "WigleWifi":
            fileinfo["app"] = firststr[0][:9]
        #elif == "Kismet":
    #elif fileinfo["type"] == "sqlite":

    # Get info
    if fileinfo["app"] ==  "WigleWifi":
        if fileinfo["type"] == "csv":
            fileinfo["version"] = firststr[0]
            fileinfo["device"] = firststr[2][6:]
            next(csv_data)
            firsttime = next(csv_data)[3]
            loc = 0
            for line in csv_data:
                endtime = line[3]
                if line[10] == "WIFI": loc += 1
            fileinfo["time"] = firsttime + " - " + endtime
            fileinfo["location"] = loc
        #elif fileinfo["type"] == "sqlite":
    #elif fileinfo["app"] ==  "Kismet":

    return fileinfo

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
    """imports data from a wigle csv file into the application database"""
    with app.app_context():
        target = os.path.join(app.config['APP_ROOT'], 'upload/')
        path = "/".join([target, filename])
        extension = filename.rsplit('.', 1)[1]
        if extension == "gz":
            f_csv = gzip.open(path, 'rt', encoding="latin-1")
        elif extension == "csv":
            f_csv = open(path, "r", encoding="latin-1")
        csv_data = csv.reader((line.replace('\0', '') for line in f_csv), delimiter=',', quotechar='"')
        next(csv_data)
        time.sleep(1)
        aplist = {}
        numberloc = 0
        numberap = 0
        lasttime = 0
        for line in csv_data:
            if line[10] == "WIFI" and float(line[9]) < float(accuracy):
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
            apindb = get_ap_in_db(bssid)
            msg = {"msg": "importinfo"}
            if len(apindb) == 1:      #if the database already has only one access point with this bssid
                if apindb[0]["ssid"] != aplist[bssid]["ssid"] or apindb[0]["capabilities"] != aplist[bssid]["capabilities"]:
                    ap_change(apindb[0], aplist[bssid])
                numberaddloc = add_loc_in_db(apindb[0]["id"], aplist[bssid]["location"], deviceid)
                addedloc += numberaddloc
                calc_ap_coord(apindb[0]["id"])
                msg["info"] = 'The access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} is already in the database. {2} new locations imported'.format(bssid, aplist[bssid]["ssid"], numberaddloc, apindb[0]["id"])
            elif len(apindb) > 1:     #if the database already has multiple access points with this bssid             !!!!!!!!!!!!!!!!!!!!!!!
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
        curent_db_info_update()

def ap_change(apindb, newap):
    """records ssid, capabilities, and time from imported data other than stored in the application database."""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(time) FROM location WHERE apid=?", (apindb["id"],))
        dblasttime = time.strptime(cursor.fetchone()[0], "%Y-%m-%d %H:%M:%S")
        newlasttime = time.strptime("1970-01-01 05:00:00", "%Y-%m-%d %H:%M:%S")
        for loc in newap["location"]:
            print(loc["time"])
            if time.strptime(loc["time"], "%Y-%m-%d %H:%M:%S") > newlasttime:
                newlasttime = time.strptime(loc["time"], "%Y-%m-%d %H:%M:%S")
        print(dblasttime)
        print(newlasttime)
        if newlasttime > dblasttime:
            print("PISHHH")
            cursor.execute("SELECT ssid, capabilities FROM ap WHERE id=?", (apindb["id"],))
            res = cursor.fetchone()
            oldssid = res[0]
            oldcapabilities = res[1]
            cursor.execute("INSERT INTO apchange ('apid', 'ssid', 'capabilities', 'time') VALUES(?, ?, ?, ?)", (apindb["id"], oldssid, oldcapabilities, time.strftime("%Y-%m-%d %H:%M:%S", dblasttime)))
            cursor.execute("UPDATE ap SET ssid = ?, capabilities = ? WHERE id = ?", (newap["ssid"], newap["capabilities"], apindb["id"]))
        else:
            cursor.execute("INSERT INTO apchange ('apid', 'ssid', 'capabilities', 'time') VALUES(?, ?, ?, ?)", (apindb["id"], newap["ssid"], newap["capabilities"], time.strftime("%Y-%m-%d %H:%M:%S" ,newlasttime)))
        conn.commit()
        conn.close()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':

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

def get_ap_in_db(bssid):
    """Returns a list of access point IDs, ssid and capabilities stored in the database with the specified bssid"""
    aps = []
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        for ap in cursor.execute("SELECT id, ssid, capabilities FROM ap WHERE bssid=?", (bssid,)):
            aps.append({"id": ap[0], "ssid": ap[1], "capabilities": ap[2]}, )
        conn.close()
    #elif app.config['CURRENT_DB_TYPE'] == 'mysql':

    return aps

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
    """function updates the access point record after adding new locations"""
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

def curent_db_info_update():
    """function updates information about the current database (number of records, time)
    in the application database"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ap")
        numberap = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM location")
        numberloc = cursor.fetchone()[0]
        cursor.execute("SELECT MIN(time) FROM location")
        firsttime = cursor.fetchone()[0]
        cursor.execute("SELECT MAX(time) FROM location")
        lasttime = cursor.fetchone()[0]
        conn.close()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':

    conn = sqlite3.connect(os.path.join(os.getcwd(), 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute('UPDATE databases SET numberofap=? WHERE id=?', (numberap, app.config['CURRENT_DB_ID']))
    cursor.execute('UPDATE databases SET numberofloc=? WHERE id=?', (numberloc, app.config['CURRENT_DB_ID']))
    cursor.execute('UPDATE databases SET timefirst=? WHERE id=?', (firsttime, app.config['CURRENT_DB_ID']))
    cursor.execute('UPDATE databases SET timelast=? WHERE id=?', (lasttime, app.config['CURRENT_DB_ID']))
    conn.commit()
    conn.close()

