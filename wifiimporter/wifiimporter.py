import pymysql
import pandas as pd

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
        netdict = [{"netid": x[0], "bssid": x[1], "ssid": x[2], "capabilities": x[3]} for x in cursor.fetchall()]
        resultdf = pd.DataFrame(netdict)
    conn.close()
    return resultdf


if __name__ == "__main__":
    import logindata
    host = logindata.host
    user = logindata.user
    password = logindata.password
    dbname = logindata.dbname
    print(appdb_network_read(host, user, password, dbname))
