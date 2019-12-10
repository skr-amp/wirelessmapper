import pymysql
import pandas as pd
import csv
from datetime import datetime
import macvendor


def str_to_unixtime(timestr):
    """ function for converting time from a string to UNIX format"""
    time = datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S')
    return int(time.timestamp() * 1000)


def channel_to_freq(channel):
    """function returns the frequency corresponding to the channel"""
    freqdict = {'1': 2412, '2': 2417, '3': 2422, '4': 2427, '5': 2432, '6': 2437, '7': 2442, '8': 2447, '9': 2452,
                '10': 2457, '11': 2462, '12': 2467, '13': 2472, '14': 2484}
    return freqdict[channel]


def freq_to_channel(freq):
    """function returns the channel corresponding to the frequency"""
    chandict = {2412: 1, 2417: 2, 2422: 3, 2427: 4, 2432: 5, 2437: 6, 2442: 7, 2447: 8, 2452: 9, 2457: 10, 2462: 11,
                2467: 12, 2472: 13, 2484: 14}
    return chandict[freq]


def appdb_mysql_create(host, user, password, dbname):
    """ function to create MySQL database named dbname"""
    conn = pymysql.connect(host, user, password)
    with conn:
        query = "CREATE DATABASE " + dbname + " DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci"
        cursor = conn.cursor()
        cursor.execute(query)

    conn = pymysql.connect(host, user, password, dbname)
    with conn:
        cursor = conn.cursor()

        query = """CREATE TABLE `device` (
                    `id` tinyint(4) NOT NULL,
                    `name` varchar(20) NOT NULL,
                    `description` varchar(50) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        cursor.execute(query)
        query = "ALTER TABLE `device` ADD PRIMARY KEY (`id`)"
        cursor.execute(query)
        query = "ALTER TABLE `device` MODIFY `id` tinyint(4) NOT NULL AUTO_INCREMENT"
        cursor.execute(query)

        query = """CREATE TABLE `location` (
                    `id` int(11) NOT NULL,
                    `netid` int(7) NOT NULL,
                    `level` tinyint(4) NOT NULL,
                    `lat` varchar(30) NOT NULL,
                    `lon` varchar(30) NOT NULL,
                    `altitude` varchar(30) NOT NULL,
                    `accuracy` varchar(30) NOT NULL,
                    `time` varchar(30) NOT NULL,
                    `device_id` tinyint(4) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        cursor.execute(query)
        query = "ALTER TABLE `location` ADD PRIMARY KEY (`id`), ADD KEY `netid` (`netid`)"
        cursor.execute(query)
        query = "ALTER TABLE `location` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT"
        cursor.execute(query)

        query = """CREATE TABLE `network` (
                    `netid` int(11) NOT NULL,
                    `bssid` varchar(17) NOT NULL,
                    `ssid` tinytext CHARACTER SET utf8mb4 NOT NULL,
                    `frequency` smallint(4) NOT NULL,
                    `capabilities` varchar(60) NOT NULL,
                    `lasttime` char(13) DEFAULT NULL,
                    `bestlevel` tinyint(4) DEFAULT NULL,
                    `bestlat` varchar(20) DEFAULT NULL,
                    `bestlon` varchar(20) DEFAULT NULL,
                    `channel` tinyint(2) DEFAULT NULL,
                    `band` varchar(7) DEFAULT NULL,
                    `vendor` tinytext
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        cursor.execute(query)
        query = "ALTER TABLE `network` ADD PRIMARY KEY (`netid`), ADD KEY `bssid` (`bssid`)"
        cursor.execute(query)
        query = "ALTER TABLE `network` MODIFY `netid` int(11) NOT NULL AUTO_INCREMENT"
        cursor.execute(query)

        query = """CREATE TABLE `ssidchange` (
                    `id` int(11) NOT NULL,
                    `netid` int(11) NOT NULL,
                    `ssid` varchar(40) NOT NULL,
                    `capabilities` varchar(60) NOT NULL,
                    `time` varchar(13) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8"""
        cursor.execute(query)
        query = "ALTER TABLE `ssidchange` ADD PRIMARY KEY (`id`)"
        cursor.execute(query)
        query = "ALTER TABLE `ssidchange` MODIFY `id` int(11) NOT NULL AUTO_INCREMENT"
        cursor.execute(query)


def appdb_network_read(appdb):
    """ function to read the list of networks from the application database """
    query = "SELECT netid, bssid, ssid, capabilities FROM network"
    if appdb[0] == "mysql":
        conn = pymysql.connect(appdb[1]["host"], appdb[1]["user"], appdb[1]["password"], appdb[1]["dbname"])
        with conn:
            cursor = conn.cursor()
            cursor.execute(query)
            netlist = [{"netid": x[0], "bssid": x[1], "ssid": x[2], "capabilities": x[3]} for x in cursor.fetchall()]
            resultdf = pd.DataFrame(netlist)
        conn.close()
    return resultdf


def appdb_location_read(appdb, netid):
    """ function to read the list of location from the application database by netid """
    query = "SELECT level, lat, lon, altitude, accuracy, time FROM location WHERE netid = '" + str(netid) + "'"
    if appdb[0] == "mysql":
        conn = pymysql.connect(appdb[1]["host"], appdb[1]["user"], appdb[1]["password"], appdb[1]["dbname"])
        with conn:
            cursor = conn.cursor()
            cursor.execute(query)
            loclist = [{"level": x[0], "lat": x[1], "lon": x[2], "altitude": x[3], "accuracy": x[4], "time": x[5]} for x in
                       cursor.fetchall()]
            result = pd.DataFrame(loclist)
        conn.close()
    return result


def appdb_network_add(appdb, bssid, ssid, frequency, capabilities):
    """function adds a new record to the application database "network" table and returns the id of this record"""
    query = "INSERT INTO `network` (`netid`, `bssid`, `ssid`, `frequency`, `capabilities`) VALUES (NULL, '" + bssid + "', '" + pymysql.escape_string(
        ssid) + "', '" + str(frequency) + "', '" + capabilities + "')"
    if appdb[0] == "mysql":
        conn = pymysql.connect(appdb[1]["host"], appdb[1]["user"], appdb[1]["password"], appdb[1]["dbname"])
        with conn:
            cursor = conn.cursor()
            cursor.execute(query)
            cursor.execute("SELECT LAST_INSERT_ID()")
            Id = cursor.fetchone()
        conn.close()
    return Id[0]


def appdb_network_update(appdb, netid, bestlevel, bestlat, bestlon, channel, band, vendor):
    """function updates the network record in the application database based on location records"""
    query = "UPDATE `network` SET `lasttime` = '0', `bestlevel` = '" + str(bestlevel) + "', `bestlat` = '" + str(
        bestlat) + "', `bestlon` = '" + str(bestlon) + "', `channel` = '" + str(channel) + "', `band` = '" + str(
        band) + "', `vendor` = '" + str(vendor) + "' WHERE `network`.`netid` = " + str(netid)
    if appdb[0] == "mysql":
        conn = pymysql.connect(appdb[1]["host"], appdb[1]["user"], appdb[1]["password"], appdb[1]["dbname"])
        with conn:
            cursor = conn.cursor()
            cursor.execute(query)
        conn.close()


def appdb_newnetwork(appdb, network, locationdf, device, accuracy):
    """function of adding a network and its locations to the application database if the network was not there"""
    location = locationdf.loc[(locationdf["bssid"] == network["bssid"]) & (locationdf["accuracy"] < accuracy)]
    if not location.empty:
        netid = appdb_network_add(appdb, network['bssid'], network['ssid'], network['frequency'], network[
            'capabilities'])  # Add the network to the application database. The function returns the Net Id of the last added network
        deviceid = get_device_id(appdb, device)  # Get the device id from the application database
        app_location_add(appdb, location, netid, deviceid)  # Add the current network locations to the application database.

        bestlevel = location['level'].max()  # Find the maximum signal strength among the records of the current network locations
        bestlat = location.loc[location['level'] == location['level'].max()]['lat'].iloc[0]  # Find the latitude of the maximum signal level
        bestlon = location.loc[location['level'] == location['level'].max()]['lon'].iloc[0]  # Find the longitude of the maximum signal level
        channel = freq_to_channel(network['frequency'])  # Determine the channel number by frequency
        band = freq_band(network['frequency'])
        vendor = macvendor.GetVendor(network['bssid'])  # Determine the manufacturer at the mac address

        appdb_network_update(appdb, netid, bestlevel, bestlat, bestlon, channel, band, vendor)  # Update the current network record in the application database
        return {"netid": netid, "bssid": network["bssid"], "ssid": network['ssid'], "numberloc": len(location)}


def get_device_id(appdb, devicename):
    """function returns the device id from the application database. If there is no such device in the database, then it is added"""
    if appdb[0] == "mysql":
        conn = pymysql.connect(appdb[1]["host"], appdb[1]["user"], appdb[1]["password"], appdb[1]["dbname"])
        with conn:
            cursor = conn.cursor()
            query = "SELECT id FROM device WHERE name = '" + devicename + "'"
            cursor.execute(query)
            id = cursor.fetchone()
            if id != None:
                return id[0]
            else:
                query = "INSERT INTO `device` (`id`, `name`, `description`) VALUES (NULL, '" + devicename + "', '')"
                cursor.execute(query)
                cursor.execute("SELECT LAST_INSERT_ID()")
                id = cursor.fetchone()
                return id[0]



def app_location_add(appdb, locations, netid, deviceid):
    """function writes location to the application database"""
    query = "INSERT INTO location (id, netid, level, lat, lon, altitude, accuracy, time, device_id) VALUES "
    for index, location in locations.iterrows():
        query += "(NULL, '" + str(netid) + "', '" + str(location['level']) + "', '" + str(location['lat']) + "', '" + str(
            location['lon']) + "', '" + str(location['altitude']) + "', '" + str(location['accuracy']) + "', '" + str(
            int(location['time'])) + "', '" + str(deviceid) + "'), "
    query = query[:-2]

    if appdb[0] == "mysql":
        conn = pymysql.connect(appdb[1]["host"], appdb[1]["user"], appdb[1]["password"], appdb[1]["dbname"])
        with conn:
            cursor = conn.cursor()
            cursor.execute(query)
        conn.close()


def freq_band(freq):
    """return 2.4ghz"""
    if (2412 <= freq) & (freq <= 2484):
        return '2.4ghz'


def wiglecsv_network_read(locdf):
    """ function to get the list of networks contained in dataframe obtained from the WiGLE csv file
        argument: dataframe containing the location recorded in the WiGLE csv file returned function wiglecsv_location_read
        return: dataframe containing the network recorded in the WiGLE csv file
    """
    networkdf = locdf.groupby('bssid', as_index=False).first()[["bssid", "ssid", "frequency", "capabilities"]]
    return networkdf


def wiglecsv_location_read(path):
    """ function to read the list of location from WiGLE csv file
        argument: WiGLE csv file path
        return: dataframe containing the location recorded in the WiGLE csv file
    """
    f_csv = open(path, "r", encoding="UTF8")
    csv_data = csv.reader(f_csv, delimiter=',', quotechar='"')
    next(csv_data)
    next(csv_data)
    loclist = [{"bssid": x[0], "ssid": x[1], "capabilities": x[2], "time": str_to_unixtime(x[3]),
                "frequency": channel_to_freq(x[4]), "level": x[5], "lat": x[6], "lon": x[7], "altitude": x[8],
                "accuracy": x[9]} for x in csv_data if x[10] == "WIFI" and x[3][:4] != "1970"]
    result = pd.DataFrame(loclist)
    result["accuracy"] = result["accuracy"].apply(pd.to_numeric)
    result["level"] = result["level"].apply(pd.to_numeric)
    return result


def wiglecsv_device_read(path):
    """ function returns the device model from the WiGLE csv file
        argument: WiGLE csv file path
        return: string containing the device model from the WiGLE csv file
    """
    f_csv = open(path, "r", encoding="UTF8")
    csv_data = csv.reader(f_csv, delimiter=',', quotechar='"')
    return next(csv_data)[2][6:]


def appdb_import(appdb, importnetworkdf, importlocationdf, device, accuracy):
    """The function adds the data read when importing the application database"""
    appdbnetwork = appdb_network_read(appdb)
    for index, network in importnetworkdf.iterrows():
        if appdbnetwork.empty:  # there are no entries in the network table of the application database
            networkcontaindb = appdbnetwork
        else:
            networkcontaindb = appdbnetwork.loc[appdbnetwork["bssid"] == network["bssid"]]

        if networkcontaindb.empty:  # there are no records with the current bssid in the database
            print("network not in app database")
            result = appdb_newnetwork(appdb, network, importlocationdf, device, accuracy)
            if result != None:
                print("Network with bssid:" + result["bssid"] + " ssid:" + result["ssid"] + " added. Assigned id:" + str(result["netid"]) + ". " + str(result["numberloc"]) + " locations added.")
            else:
                print("Network with bssid:" + result["bssid"] + " ssid:" + result["ssid"] + " not added.")
        elif len(networkcontaindb) == 1:  # the database has one record with the current bssid
            print("network is in app database")
        else:  # there are several records with the current bssid in the database
            print("the database has " + str(len(networkcontaindb)) + " records with the current bssid")


if __name__ == "__main__":
    import logindata

    host = logindata.host
    user = logindata.user
    password = logindata.password
    dbname = "test"
    netid = 2
    path = "test.csv"
    accuracy = 20
    appdb = ("mysql", {"host": host, "user": user, "password": password, "dbname": dbname})

    importlocationdf = wiglecsv_location_read(path)
    importnetworkdf = wiglecsv_network_read(importlocationdf)
    device = wiglecsv_device_read(path)
    appdb_import(appdb, importnetworkdf, importlocationdf, device, accuracy)
