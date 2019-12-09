import os
import sqlite3
import re

path = os.path.dirname(os.path.abspath(__file__))

conn = sqlite3.connect(os.path.join(path, "mac_db.sqlite"))
cursor = conn.cursor()

def GetVendor(query):
	path = os.path.dirname(os.path.abspath(__file__))
	conn = sqlite3.connect(os.path.join(path, "mac_db.sqlite"))
	cursor = conn.cursor()
	
	query = query.upper()
	query = re.sub(r'\W+', '', query)
	
	cursor.execute("SELECT * FROM oui WHERE Assignment=(?)", (query[:6],))
	response = cursor.fetchone()
	
	if response != None:
		if response[1] == "Private":
			result = "Private"
		else:
			if response[1] !="IEEE Registration Authority":
				result = response[1]
			else:
				cursor.execute("SELECT * FROM mam WHERE Assignment=(?)", (query[:7],))
				response = cursor.fetchone()
				if response != None:
					if response[1] == "Private":
						result = "Private"
					else:
						result = response[1]
				else:
					cursor.execute("SELECT * FROM oui36 WHERE Assignment=(?)", (query[:9],))
					response = cursor.fetchone()
					if response[1] == "Private":
						result = "Private"
					else:
						result = response[1]
	else:
		result = "Not found"
	
	conn.close()
	return result