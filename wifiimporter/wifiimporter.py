import pymysql
import pandas as pd
import csv
from datetime import datetime


def str_to_unixtime(timestr):
    """ function for converting time from a string to UNIX format"""
    time = datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S')
    return int(time.timestamp() * 1000)


def channel_to_freq(channel):
    """function returns the frequency corresponding to the channel"""
    freqdict = {'1':2412, '2':2417, '3':2422, '4':2427, '5':2432, '6':2437, '7':2442, '8':2447, '9':2452, '10':2457, '11':2462, '12':2467, '13':2472, '14':2484}
    return freqdict[channel]


def mysql_db_create(host, user, password, dbname):
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


def appdb_network_read(host, user, password, dbname):
    """ function to read the list of networks from the application database """
    query = "SELECT netid, bssid, ssid, capabilities FROM network"
    conn = pymysql.connect(host, user, password, dbname)
    with conn:
        cursor = conn.cursor()
        cursor.execute(query)
        netlist = [{"netid": x[0], "bssid": x[1], "ssid": x[2], "capabilities": x[3]} for x in cursor.fetchall()]
        resultdf = pd.DataFrame(netlist)
    conn.close()
    return resultdf


def appdb_location_read(host, user, password, dbname, netid):
    """ function to read the list of location from the application database by netid """
    query = "SELECT level, lat, lon, altitude, accuracy, time FROM location WHERE netid = '" + str(netid) + "'"
    conn = pymysql.connect(host, user, password, dbname)
    with conn:
        cursor = conn.cursor()
        cursor.execute(query)
        loclist = [{"level": x[0], "lat": x[1], "lon": x[2], "altitude": x[3], "accuracy": x[4], "time": x[5]} for x in cursor.fetchall()]
        result = pd.DataFrame(loclist)
    conn.close()
    return result


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
    #next(csv_data)
    loclist = [{"bssid": x[0], "ssid": x[1], "capabilities": x[2], "time": str_to_unixtime(x[3]), "frequency": channel_to_freq(x[4]), "level": x[5], "lat": x[6], "lon": x[7], "altitude": x[8], "accuracy": x[9]} for x in csv_data if x[10] == "WIFI" and x[3][:4] != "1970"]
    result = pd.DataFrame(loclist)
    return result


def wiglecsv_device_read(path):
    """ function returns the device model from the WiGLE csv file
        argument: WiGLE csv file path
        return: string containing the device model from the WiGLE csv file
    """
    f_csv = open(path, "r", encoding="UTF8")
    csv_data = csv.reader(f_csv, delimiter=',', quotechar='"')
    return next(csv_data)[2][6:]


if __name__ == "__main__":
    import logindata
    host = logindata.host
    user = logindata.user
    password = logindata.password
    dbname = logindata.dbname
    netid = 2

    path = "2.csv"
    csvdf = wiglecsv_location_read(path)
    print(csvdf)
    print(wiglecsv_network_read(csvdf)["ssid"])
    print(wiglecsv_device_read(path))