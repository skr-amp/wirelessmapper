import csv
import time, datetime
import os
import sqlite3
import pymysql
import gzip
import pathlib
from collections import Counter
from wifiapp import app
from wifiapp.macvendor import GetVendor
from flask import flash

importrun = False

def check_file(filename):
    """Getting information about a imported file"""
    fileinfo = {}
    target = os.path.join(app.config['APP_ROOT'], 'upload')
    path = os.path.join(target, filename)
    extension = pathlib.Path(path).suffixes
    fileinfo["filesize"] = os.path.getsize(path)

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
    feature =0
    if fileinfo["app"] ==  "WigleWifi":
        if fileinfo["type"] == "csv":
            fileinfo["version"] = firststr[0]
            fileinfo["device"] = firststr[2][6:]
            next(csv_data)
            fileinfo["firsttime"] = next(csv_data)[3]
            loc = 1
            networks = set()
            feature = int(datetime.datetime.strptime(fileinfo["firsttime"], "%Y-%m-%d %H:%M:%S").timestamp())
            for line in csv_data:
                lasttime = line[3]
                if line[10] == "WIFI":
                    loc += 1
                    networks.add(line[0])
            feature += int(datetime.datetime.strptime(lasttime, "%Y-%m-%d %H:%M:%S").timestamp())
            fileinfo["lasttime"] = lasttime
            fileinfo["network"] = len(networks)
            fileinfo["location"] = loc
            fileinfo["feature"] = feature
        elif fileinfo["type"] == "sqlite":
            fileinfo["device"] = None
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT datetime(MIN(time)/1000, 'unixepoch', 'localtime') FROM location WHERE time>0")
            fileinfo["firsttime"] = cursor.fetchone()[0]
            cursor.execute("SELECT datetime(MAX(time)/1000, 'unixepoch', 'localtime') FROM location")
            fileinfo["lasttime"] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM network WHERE type="W"')
            fileinfo["network"] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM location LEFT JOIN network ON network.bssid=location.bssid WHERE network.type="W" and time>0')
            fileinfo["location"] = cursor.fetchone()[0]
            for time in cursor.execute("SELECT time FROM location LIMIT 10"):
                feature += int(time[0]/1000)
            fileinfo["feature"] = feature
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

def wigle_csv_import(app, socketio, filename, accuracy, deviceid, feature):
    """imports data from a wigle csv file into the application database"""
    target = os.path.join(app.config['APP_ROOT'], 'upload')
    path = os.path.join(target, filename)
    filesize = os.path.getsize(path)
    extension = filename.rsplit('.', 1)[1]
    if extension == "gz":
        f_csv = gzip.open(path, 'rt', encoding="latin-1")
    elif extension == "csv":
        f_csv = open(path, "r", encoding="latin-1")
    csv_data = csv.reader((line.replace('\0', '') for line in f_csv), delimiter=',', quotechar='"')
    next(csv_data)
    importap = {}
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
            lasttime = loctime
            if len(importap) == 0 or not bssid in importap.keys():
                importap[bssid] = {"ssid": ssid, "capabilities": capabilities, "frequency": channel_to_freq(channel),
                                 "locations": {(loclat, loclon, localtitude, locaccuracy, loclevel, loctime, deviceid)}}
                numberap += 1
            else:
                importap[bssid]["locations"].add((loclat, loclon, localtitude, locaccuracy, loclevel, loctime, deviceid))
    time.sleep(1)
    socketio.emit('numberaploc', (filename.replace(".", ""), numberap, numberloc, accuracy), namespace='/importer',
                  broadcast=True)
    print(numberap)
    print(numberloc)

    sortedbssids = sorted(importap)
    print(sortedbssids)

    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        curentdbconn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        curentdbcursor = curentdbconn.cursor()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    curentdbcursor.execute('SELECT lastimportbssid, checkloc FROM importfiles WHERE filefeature=? AND filesize=? AND importaccuracy=?',
                           (feature, filesize, accuracy))
    res=curentdbcursor.fetchone()
    if res:
        lastimportbssid = res[0]
        checkloc = res[1]
    else:
        curentdbcursor.execute("INSERT INTO importfiles ('filefeature', 'filesize', 'filetype', 'importaccuracy') VALUES(?, ?, ?, ?)",
            (feature, filesize, 'csv', accuracy))
        curentdbconn.commit()
        lastimportbssid = "0"
        checkloc = 0

    addedap = 0
    addedloc = 0
    apdblist = get_list_ap_in_db()
    for bssid in sortedbssids:
        print(bssid)
        print(importrun)
        if not importrun:
            curentdbconn.close()
            break
        if bssid > lastimportbssid:
            if bssid in apdblist.keys():
                if apdblist[bssid]["count"] == 1:  # if the database already has only one access point with this bssid
                    if apdblist[bssid]["info"][0]["ssid"] != importap[bssid]["ssid"] or apdblist[bssid]["info"][0]["capabilities"] != importap[bssid]["capabilities"]:
                         ap_change(apdblist[bssid]["info"][0], importap[bssid])
                    numberaddloc = add_loc_in_db(apdblist[bssid]["info"][0]["id"], importap[bssid]["locations"])
                    addedloc += numberaddloc
                    importmsg = 'The access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} is already in the database. {2} new locations imported'.format(
                                bssid, importap[bssid]["ssid"], numberaddloc, apdblist[bssid]["info"][0]["id"])
                    if numberaddloc > 0: calc_ap_coord(apdblist[bssid]["info"][0]["id"])
                elif apdblist[bssid]["count"] > 1:     #if the database already has multiple access points with this bssid             !!!!!!!!!!!!!!!!!!!!!!!
                    print("More than one access point with such bssid in the database: " + bssid)
            else:  # there are no access points with this bssid in the database
                id = add_ap_in_db({"bssid": bssid, "ssid": importap[bssid]["ssid"], "capabilities": importap[bssid]["capabilities"], "frequency": importap[bssid]["frequency"]})
                addedap += 1
                numberaddloc = add_loc_in_db(id, importap[bssid]["locations"])
                addedloc += numberaddloc
                importmsg = 'A new access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} has been added to the database. {2} new locations imported'.format(
                    bssid, importap[bssid]["ssid"], numberaddloc, id)
                if numberaddloc > 0: calc_ap_coord(id)
            checkloc += len(importap[bssid]["locations"])
            socketio.emit('importinfo', importmsg, namespace='/importer', broadcast=True)
            progress = (checkloc * 100) // numberloc
            socketio.emit('checkloc', (filename.replace(".", ""), progress), namespace='/importer', broadcast=True)

            curentdbcursor.execute(
                "UPDATE importfiles SET lastimportbssid=?, checkloc=? WHERE filefeature=? AND filesize=? AND importaccuracy=?",
                (bssid, checkloc, feature, filesize, accuracy))
            curentdbconn.commit()

    if importrun:
        curent_db_info_update()
        importtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        curentdbcursor.execute(
                "UPDATE importfiles SET importtime=? WHERE filefeature=? AND filesize=? AND importaccuracy=?",
                (importtime, feature, filesize, accuracy))
        curentdbconn.commit()
        curentdbconn.close()
        resultmsg = 'Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
    else:
        resultmsg = 'Import stopped. Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
    socketio.emit('resultinfo', (filename.replace(".", ""), resultmsg), namespace='/importer', broadcast=True)

def wigle_sqlite_import(app, socketio, filename, accuracy, deviceid, feature):
    """imports data from a backup sqlite database wigle file into the application database"""
    time.sleep(1)
    target = os.path.join(app.config['APP_ROOT'], 'upload')
    path = os.path.join(target, filename)
    filesize = os.path.getsize(path)
    importfirsttime = get_import_firsttime(feature, accuracy)
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        curentdbconn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        curentdbcursor = curentdbconn.cursor()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    curentdbcursor.execute('SELECT lastimportbssid, checkloc FROM importfiles WHERE filefeature=? AND filesize=? AND importaccuracy=?',
                           (feature, filesize, accuracy))
    res=curentdbcursor.fetchone()
    if res:
        lastimportbssid = res[0]
        checkloc = res[1]
    else:
        curentdbcursor.execute("INSERT INTO importfiles ('filefeature', 'filesize', 'filetype', 'importaccuracy') VALUES(?, ?, ?, ?)",
            (feature, filesize, 'sqlite', accuracy))
        curentdbconn.commit()
        lastimportbssid = 0
        checkloc = 0

    importconn = sqlite3.connect(path)
    importcursor = importconn.cursor()
    importcursor.execute(
        'SELECT COUNT(DISTINCT network.bssid) FROM network LEFT JOIN location ON network.bssid=location.bssid WHERE network.type="W" AND location.time>? AND location.accuracy<?',
        (importfirsttime, accuracy))
    numberap = importcursor.fetchone()[0]
    importcursor.execute(
        'SELECT COUNT(*) FROM location LEFT JOIN network ON network.bssid=location.bssid WHERE network.type="W" AND location.time>? AND location.accuracy<?', (importfirsttime, accuracy))
    numberloc = importcursor.fetchone()[0]
    socketio.emit('numberaploc', (filename.replace(".", ""), numberap, numberloc, accuracy), namespace='/importer', broadcast=True)

    importaplist = []
    for ap in importcursor.execute('SELECT DISTINCT network.bssid, ssid, frequency, capabilities FROM network LEFT JOIN location ON network.bssid=location.bssid WHERE network.type="W" AND location.time>? AND location.accuracy<? AND location.bssid>? ORDER BY network.bssid',
            (importfirsttime, accuracy, lastimportbssid)):
        importaplist.append({"bssid": ap[0], "ssid": ap[1], "frequency": ap[2], "capabilities": ap[3]})

    addedap = 0
    addedloc = 0
    apdblist = get_list_ap_in_db()
    for ap in importaplist:
        if not importrun:
            importconn.close()
            curentdbconn.close()
            break
        if ap["bssid"] in apdblist.keys():
            if apdblist[ap["bssid"]]["count"] == 1:  # if the database already has only one access point with this bssid
                importcursor.execute("SELECT lat, lon, altitude, accuracy, level, datetime(time/1000, 'unixepoch', 'localtime') FROM location WHERE bssid=? AND location.time>? AND location.accuracy<?", (ap["bssid"], importfirsttime, accuracy))
                locations = set((int(float(x[0]) * 1000000), int(float(x[1]) * 1000000), int(float(x[2]) * 100), int(float(x[3]) * 100), x[4], x[5], int(deviceid)) for x in importcursor.fetchall())
                ap["location"] = locations
                if apdblist[ap["bssid"]]["info"][0]["ssid"] != ap["ssid"] or apdblist[ap["bssid"]]["info"][0]["capabilities"] != ap["capabilities"]:
                     ap_change(apdblist[ap["bssid"]]["info"][0], ap)
                numberaddloc = add_loc_in_db(apdblist[ap["bssid"]]["info"][0]["id"], locations)
                addedloc += numberaddloc
                importmsg = 'The access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} is already in the database. {2} new locations imported'.format(
                            ap["bssid"], ap["ssid"], numberaddloc, apdblist[ap["bssid"]]["info"][0]["id"])
                if numberaddloc > 0: calc_ap_coord(apdblist[ap["bssid"]]["info"][0]["id"])
            elif apdblist[ap["bssid"]]["count"] > 1:     #if the database already has multiple access points with this bssid             !!!!!!!!!!!!!!!!!!!!!!!
                print("More than one access point with such bssid in the database: " + ap["bssid"])
        else:  # there are no access points with this bssid in the database
            importcursor.execute("SELECT lat, lon, altitude, accuracy, level, datetime(time/1000, 'unixepoch', 'localtime') FROM location WHERE bssid=? AND location.time>? AND location.accuracy<?", (ap["bssid"], importfirsttime, accuracy))
            locations = set((int(float(x[0]) * 1000000), int(float(x[1]) * 1000000), int(float(x[2]) * 100), int(float(x[3]) * 100), int(x[4]), x[5], int(deviceid)) for x in importcursor.fetchall())
            id = add_ap_in_db({"bssid": ap["bssid"], "ssid": ap["ssid"], "capabilities": ap["capabilities"], "frequency": ap["frequency"]})
            addedap += 1
            numberaddloc = add_loc_in_db(id, locations)
            addedloc += numberaddloc
            importmsg = 'A new access point with bssid: <a href="/location/{3}" target="_blank">{0}</a> and ssid: {1} has been added to the database. {2} new locations imported'.format(
                ap["bssid"], ap["ssid"], numberaddloc, id)
            if numberaddloc > 0: calc_ap_coord(id)
        checkloc += len(locations)
        socketio.emit('importinfo', importmsg, namespace='/importer', broadcast=True)
        progress = (checkloc*100)//numberloc
        socketio.emit('checkloc', (filename.replace(".", ""), progress), namespace='/importer', broadcast=True)

        curentdbcursor.execute("UPDATE importfiles SET lastimportbssid=?, checkloc=? WHERE filefeature=? AND filesize=? AND importaccuracy=?",
                (ap["bssid"], checkloc, feature, filesize, accuracy))
        curentdbconn.commit()

    if importrun:
        curent_db_info_update()
        importconn.close()
        importtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        curentdbcursor.execute("UPDATE importfiles SET importtime=? WHERE filefeature=? AND filesize=? AND importaccuracy=?",
            (importtime, feature, filesize, accuracy))
        curentdbconn.commit()
        curentdbconn.close()
        resultmsg = 'Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
    else:
        resultmsg = 'Import stopped. Imported new access points: {0} Imported new locations: {1}'.format(addedap, addedloc)
    socketio.emit('resultinfo', (filename.replace(".", ""), resultmsg), namespace='/importer', broadcast=True)

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
        if locaddcount ==0: return locaddcount
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

def add_file_to_appdb(filename):
    """"""
    uploadtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fileinfo = check_file(filename)
    conn = sqlite3.connect(os.path.join(app.config['APP_ROOT'], 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM uploadsource WHERE feature=?", (fileinfo["feature"],))
    sourceid = cursor.fetchone()
    if not sourceid:
        cursor.execute("INSERT INTO uploadsource ('feature', 'type', 'app', 'firsttime', 'lasttime', 'device') VALUES(?, ?, ?, ?, ?, ?)",
                       (fileinfo['feature'], fileinfo['type'], fileinfo['app'], fileinfo['firsttime'], fileinfo['firsttime'], fileinfo['device']))
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ROWID()")
        sourceid = cursor.fetchone()
    if fileinfo["type"] == "csv":
        cursor.execute("SELECT filename, uploadtime FROM uploadfiles WHERE sourceid=?", (sourceid[0],))
        fileindb = cursor.fetchone()
        if fileindb:
            flash("The file with this data was uploaded earlier on " + fileindb[1] + " with the name " + fileindb[0], "error")
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.close()
            return False
        else:
            cursor.execute("INSERT INTO uploadfiles ('sourceid', 'filename', 'filesize', 'uploadtime', 'firsttime', 'lasttime', 'numberap', 'numberloc') VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                           (sourceid[0], filename, fileinfo["filesize"],  uploadtime, fileinfo["firsttime"], fileinfo["lasttime"], fileinfo["network"], fileinfo["location"],))
            conn.commit()
            conn.close()
            return True
    elif fileinfo["type"] == "sqlite":
        cursor.execute("SELECT filename, uploadtime, lasttime FROM uploadfiles WHERE sourceid=?", (sourceid[0],))
        for fileindb in cursor.fetchall():
            if fileinfo["lasttime"] == fileindb[2]:
                flash("The file with this data was uploaded earlier on " + fileindb[1] + " with the name " + fileindb[0], "error")
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                conn.close()
                return False

        cursor.execute(
                "INSERT INTO uploadfiles ('sourceid', 'filename', 'filesize', 'uploadtime', 'firsttime', 'lasttime', 'numberap', 'numberloc') VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (sourceid[0], filename, fileinfo["filesize"], uploadtime, fileinfo["firsttime"], fileinfo["lasttime"],
                 fileinfo["network"], fileinfo["location"],))
        conn.commit()
        conn.close()
        return True

def get_source():
    """"""
    conn = sqlite3.connect(os.path.join(app.config['APP_ROOT'], 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT uploadsource.feature, uploadsource.type, uploadsource.app, uploadsource.device FROM uploadsource JOIN uploadfiles ON uploadsource.id = uploadfiles.sourceid GROUP BY uploadsource.feature ORDER BY MAX(uploadfiles.uploadtime) DESC")
    sources = []
    for source in cursor.fetchall():
        sources.append({"feature": source[0], "type": source[1], "app": source[2], "device": source[3]})
    conn.close()
    return sources

def get_uploadfiles():
    """"""
    conn = sqlite3.connect(os.path.join(app.config['APP_ROOT'], 'appdb.db'))
    cursor = conn.cursor()
    cursor.execute("SELECT feature, filename, filesize, uploadfiles.firsttime, uploadfiles.lasttime, numberap, numberloc, uploadtime FROM uploadfiles JOIN uploadsource ON uploadfiles.sourceid = uploadsource.id ORDER BY numberloc")
    files = {}
    for file in cursor.fetchall():
        if file[0] in files.keys():
            files[file[0]].append({"filename": file[1], "filesize": file[2], "firsttime": file[3], "lasttime": file[4], "numberap": file[5], "numberloc": file[6], "uploadtime": file[7], "minaccuracy": get_min_accuracy(file[0], file[2])})
        else:
            files[file[0]] = [{"filename": file[1], "filesize": file[2], "firsttime": file[3], "lasttime": file[4], "numberap": file[5], "numberloc": file[6], "uploadtime": file[7], "minaccuracy": get_min_accuracy(file[0], file[2])}]
    conn.close()
    return files

def get_importfiles():
    """"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT filefeature, filesize, MAX(importaccuracy), importtime FROM importfiles GROUP BY filefeature, filesize")
        files = {}
        for file in cursor.fetchall():
            if file[0] in files.keys():
                files[file[0]][file[1]] = {"accuracy": file[2], "importtime": file[3]}
            else:
                files[file[0]] = {file[1]:{"accuracy": file[2], "importtime": file[3]}}
        conn.close()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return files

def get_device_id(devicename):
    """"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM device WHERE devicename=?", (devicename, ))
        res = cursor.fetchone()
        if res:
            id = res[0]
        else:
            cursor.execute("INSERT INTO device ('devicename') VALUES(?)", (devicename, ))
            conn.commit()
            cursor.execute("SELECT LAST_INSERT_ROWID()")
            id = cursor.fetchone()[0]
        conn.close()
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return id

def get_min_accuracy(feature, filesize):
    """"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(importaccuracy) FROM importfiles WHERE filefeature=? AND filesize>=?", (feature, filesize))
        accuracy = cursor.fetchone()[0]
        conn.close()
        if accuracy:
            return accuracy
        else:
            return 0
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':

def get_import_firsttime(feature, accuracy):
    """"""
    if app.config['CURRENT_DB_TYPE'] == 'sqlite':
        conn = sqlite3.connect('wifiapp/localdb/' + app.config['CURRENT_DB_NAME'])
        cursor = conn.cursor()
        cursor.execute("SELECT filesize, MAX(importaccuracy) FROM importfiles WHERE filefeature=? AND importaccuracy>=? AND importtime IS NOT NULL GROUP BY filesize ORDER BY filesize DESC LIMIT 1", (feature, accuracy))
        filesize = cursor.fetchone()
        conn.close()
        print(filesize)
        if filesize:
            conn = sqlite3.connect(os.path.join(app.config['APP_ROOT'], 'appdb.db'))
            cursor = conn.cursor()
            cursor.execute("SELECT strftime('%s', uploadfiles.lasttime, 'utc') FROM uploadfiles LEFT JOIN uploadsource ON uploadfiles.sourceid=uploadsource.id WHERE uploadsource.feature=? AND uploadfiles.filesize=?", (feature, filesize[0]))
            lasttime = int(cursor.fetchone()[0])*1000
            conn.close()
            return lasttime
        else:
            return 0
    # elif app.config['CURRENT_DB_TYPE'] == 'mysql':
    return None
