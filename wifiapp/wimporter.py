import csv
import time
import os
import sqlite3
import pymysql
import gzip
import pathlib
from collections import Counter
from wifiapp import app
from wifiapp.macvendor import GetVendor


def check_file(filename):
    """Getting information about a imported file"""
    fileinfo = {}
    target = os.path.join(app.config['APP_ROOT'], 'upload')
    path = os.path.join(target, filename)
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
            fileinfo["app"] = "WigleWifi"
        #elif == "Kismet":
    elif fileinfo["type"] == "sqlite":
        wiglesqlitereq = {
            'android_metadata': {'locale'},
            'location': {'_id', 'bssid', 'level', 'lat', 'lon', 'altitude', 'accuracy', 'time'},
            'network': {'bssid', 'ssid', 'frequency', 'capabilities', 'lasttime', 'lastlat', 'lastlon', 'type', 'bestlevel', 'bestlat', 'bestlon'}}
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        tables = []
        colmatch =[]
        for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            tables.append(table[0])
        if set(wiglesqlitereq.keys()).issubset(set(tables)):
            for tab in wiglesqlitereq.keys():
                cursor.execute("select * from %s" % tab)
                colmatch.append(wiglesqlitereq[tab].issubset(set(map(lambda x: x[0], cursor.description))))
            if colmatch[0] and colmatch[1] and colmatch[2]:
                fileinfo["app"] = "WigleWifi"
        conn.close()

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
        elif fileinfo["type"] == "sqlite":
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM network WHERE type="W"')
            fileinfo["network"] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM location LEFT JOIN network ON network.bssid=location.bssid WHERE network.type="W"')
            fileinfo["location"] = cursor.fetchone()[0]
            conn.close()
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
        for line in csv_data:
            if line[10] == "WIFI" and float(line[9]) < float(accuracy):
                bssid = line[0]
                ssid = line[1]
                capabilities = line[2]
                loctime = line[3]
                channel = line[4]
                loclevel = int(line[5])
                loclat = int(float(line[6]) * 1000000)
                loclon = int(float(line[7]) * 1000000)
                localtitude = int(float(line[7]) * 100)
                locaccuracy = int(float(line[9]) * 100)
                numberloc += 1
                if len(aplist) == 0 or not bssid in aplist.keys():
                    # 0-lat 1-lon 2-altitude 3-accuracy 4-level 5-time 6-deviceid
                    aplist[bssid] = {"ssid":ssid, "capabilities":capabilities, "frequency":channel_to_freq(channel),
                                     "location":{(loclat, loclon, localtitude, locaccuracy, loclevel, loctime, deviceid)}}
                    numberap += 1
                else:
                    aplist[bssid]["location"].add((loclat, loclon, localtitude, locaccuracy, loclevel, loctime, deviceid))
        socketio.send({"msg": "number_of_loc_and_ap", "numberloc":numberloc, "numberap":numberap}, broadcast=True)

        addedap = 0
        addedloc = 0
        checkloc =0
        apdblist = get_list_ap_in_db()
        for bssid in aplist.keys():
            msg = {"msg": "importinfo"}
            if bssid in apdblist.keys():
                if apdblist[bssid]["count"] == 1:      #if the database already has only one access point with this bssid
                    if apdblist[bssid]["info"][0]["ssid"] != aplist[bssid]["ssid"] or apdblist[bssid]["info"][0]["capabilities"] != aplist[bssid]["capabilities"]:
                        ap_change(apdblist[bssid]["info"][0], aplist[bssid])
                    numberaddloc = add_loc_in_db(apdblist[bssid]["info"][0]["id"], aplist[bssid]["location"])
                    addedloc += numberaddloc
                    if numberaddloc > 0: calc_ap_coord(apdblist[bssid]["info"][0]["id"])
                    msg["info"] = 'The access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} is already in the database. {2} new locations imported'.format(bssid, aplist[bssid]["ssid"], numberaddloc, apdblist[bssid]["info"][0]["id"])
                elif apdblist[bssid]["count"] > 1:     #if the database already has multiple access points with this bssid             !!!!!!!!!!!!!!!!!!!!!!!
                    print("More than one access point with such bssid in the database: " + bssid)
            else:                   #there are no access points with this bssid in the database
                id = add_ap_in_db({"bssid":bssid, "ssid":aplist[bssid]["ssid"], "capabilities":aplist[bssid]["capabilities"], "frequency":aplist[bssid]["frequency"] })
                addedap += 1
                numberaddloc = add_loc_in_db(id, aplist[bssid]["location"])
                addedloc += numberaddloc
                if numberaddloc > 0: calc_ap_coord(id)
                msg["info"] = 'A new access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} has been added to the database. {2} new locations imported'.format(
                    bssid, aplist[bssid]["ssid"], numberaddloc, id)
            checkloc += len(aplist[bssid]["location"])
            msg["checkloc"] = checkloc
            socketio.send(msg, broadcast=True)
        msg = {"msg": "resultinfo"}
        msg["info"] = 'Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
        socketio.send(msg, broadcast=True)
        curent_db_info_update()

def wigle_sqlite_import(app, socketio, filename, accuracy, deviceid):
    """"""
    time.sleep(1)
    target = os.path.join(app.config['APP_ROOT'], 'upload')
    path = os.path.join(target, filename)
    importconn = sqlite3.connect(path)
    importcursor = importconn.cursor()
    importcursor.execute(
        'SELECT COUNT(DISTINCT network.bssid) FROM network LEFT JOIN location ON network.bssid=location.bssid WHERE network.type="W" AND location.time>0 AND location.accuracy<?',
        (accuracy,))
    numberap = importcursor.fetchone()[0]
    importcursor.execute(
        'SELECT COUNT(*) FROM location LEFT JOIN network ON network.bssid=location.bssid WHERE network.type="W" AND location.time>0 AND location.accuracy<?', (accuracy,))
    numberloc = importcursor.fetchone()[0]
    socketio.send({"msg": "number_of_loc_and_ap", "numberloc": numberloc, "numberap": numberap}, broadcast=True)

    importaplist = []
    for ap in importcursor.execute('SELECT DISTINCT network.bssid, ssid, frequency, capabilities FROM network LEFT JOIN location ON network.bssid=location.bssid WHERE network.type="W" AND location.time>0 AND location.accuracy<?',
            (accuracy,)):
        importaplist.append({"bssid": ap[0], "ssid": ap[1], "frequency": ap[2], "capabilities": ap[3]})

    addedap = 0
    addedloc = 0
    checkloc = 0
    apdblist = get_list_ap_in_db()
    for ap in importaplist:
        msg = {"msg": "importinfo"}
        if ap["bssid"] in apdblist.keys():
            if apdblist[ap["bssid"]]["count"] == 1:  # if the database already has only one access point with this bssid
                importcursor.execute("SELECT lat, lon, altitude, accuracy, level, datetime(time/1000, 'unixepoch', 'localtime') FROM location WHERE bssid=? AND location.time>0 AND location.accuracy<?", (ap["bssid"], accuracy))
                locations = set((int(float(x[0]) * 1000000), int(float(x[1]) * 1000000), int(float(x[2]) * 100), int(float(x[3]) * 100), x[4], x[5], int(deviceid)) for x in importcursor.fetchall())
                ap["location"] = locations
                if apdblist[ap["bssid"]]["info"][0]["ssid"] != ap["ssid"] or apdblist[ap["bssid"]]["info"][0]["capabilities"] != ap["capabilities"]:
                     ap_change(apdblist[ap["bssid"]]["info"][0], ap)
                numberaddloc = add_loc_in_db(apdblist[ap["bssid"]]["info"][0]["id"], locations)
                addedloc += numberaddloc
                msg["info"] = 'The access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} is already in the database. {2} new locations imported'.format(
                            ap["bssid"], ap["ssid"], numberaddloc, apdblist[ap["bssid"]]["info"][0]["id"])
                if numberaddloc > 0: calc_ap_coord(apdblist[ap["bssid"]]["info"][0]["id"])
            elif apdblist[ap["bssid"]]["count"] > 1:     #if the database already has multiple access points with this bssid             !!!!!!!!!!!!!!!!!!!!!!!
                print("More than one access point with such bssid in the database: " + ap["bssid"])
        else:  # there are no access points with this bssid in the database
            importcursor.execute("SELECT lat, lon, altitude, accuracy, level, datetime(time/1000, 'unixepoch', 'localtime') FROM location WHERE bssid=? AND location.time>0 AND location.accuracy<?", (ap["bssid"], accuracy))
            locations = set((int(float(x[0]) * 1000000), int(float(x[1]) * 1000000), int(float(x[2]) * 100), int(float(x[3]) * 100), int(x[4]), x[5], int(deviceid)) for x in importcursor.fetchall())
            id = add_ap_in_db({"bssid": ap["bssid"], "ssid": ap["ssid"], "capabilities": ap["capabilities"], "frequency": ap["frequency"]})
            addedap += 1
            numberaddloc = add_loc_in_db(id, locations)
            addedloc += numberaddloc
            msg["info"] = 'A new access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} has been added to the database. {2} new locations imported'.format(
                ap["bssid"], ap["ssid"], numberaddloc, id)
            if numberaddloc > 0: calc_ap_coord(id)
        checkloc += len(locations)
        msg["checkloc"] = checkloc
        socketio.send(msg, broadcast=True)
    msg = {"msg": "resultinfo"}
    msg["info"] = 'Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
    socketio.send(msg, broadcast=True)
    curent_db_info_update()
    importconn.close()

def ap_change(apindb, newap):
    """records ssid, capabilities, and time from imported data other than stored in the application database."""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(time) FROM location WHERE apid=?", (apindb["id"],))
        dblasttime = time.strptime(cursor.fetchone()[0], "%Y-%m-%d %H:%M:%S")
        newlasttime = time.strptime("1970-01-01 05:00:00", "%Y-%m-%d %H:%M:%S")
        for loc in newap["location"]:
            if time.strptime(loc[5], "%Y-%m-%d %H:%M:%S") > newlasttime:
                newlasttime = time.strptime(loc[5], "%Y-%m-%d %H:%M:%S")
        if newlasttime > dblasttime:
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

def get_list_ap_in_db():
    """"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT bssid FROM ap")
        apcounter = Counter([x[0] for x in cursor.fetchall()])
        aps = {}
        for bssid in apcounter.keys():
            aps[bssid] = {"count": apcounter[bssid], "info": []}
        for ap in cursor.execute("SELECT bssid, id, ssid, capabilities FROM ap"):
            aps[ap[0]]["info"].append({"id": ap[1], "ssid":ap[2], "capabilities": ap[3]})
        conn.close()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return aps

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

def add_loc_in_db(apid, locations):
    """adds locations to the database and returns the number of added locations"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        locindb = set()
        # 0-lat 1-lon 2-altitude 3-accuracy 4-level 5-time 6-deviceid
        for loc in cursor.execute("SELECT lat, lon, altitude, accuracy, level, time, deviceid FROM location WHERE apid=?", (apid, )):
            locindb.add((loc[0], loc[1], loc[2], loc[3], loc[4], loc[5], loc[6]))
        addloc = list(locations - locindb)
        locaddcount = len(addloc)
        addloclist = []
        for loc in addloc:
            loc = list(loc)
            loc.append(apid)
            addloclist.append(loc)
        cursor.executemany("INSERT INTO location ('lat', 'lon', 'altitude', 'accuracy', 'level', 'time', 'deviceid', 'apid') VALUES(?, ?, ?, ?, ?, ?, ?, ?)", addloclist)
        conn.commit()
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

