import os
import sqlite3
from wifiapp import app, socketio
from flask import render_template, request, jsonify, redirect, url_for, flash
from threading import Thread
from wifiapp.getdbinfo import apmarkers, apinfo, locationinfo
from wifiapp.dbmanager import dblist, setdb, editdbinfo, mysqlsrvexist, createdb, adddb, deldb, delfromappdb
from wifiapp.wimporter import check_file, get_devices, add_device_db, wigle_csv_import, wigle_sqlite_import, add_file_to_appdb, get_source, get_uploadfiles, get_importfiles, get_device_id


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/getapmarkers', methods=['GET'])
def getapmarkers():
    return jsonify(apmarkers(request.args.get('bounds')))


@app.route('/getapinfo', methods=['GET'])
def getapinfo():
    return jsonify(apinfo(request.args.get('apid')))


@app.route('/location/<apid>')
def location(apid):
    return render_template('location.html', ap=locationinfo(apid))


@app.route('/dbmanager', methods=['GET', 'POST'])
def dbmanager():
    return render_template('dbmanager.html', dblist=dblist(), currentdbid=int(app.config['CURRENT_DB_ID']))


@app.route('/dbmanager/setcurentdb', methods=['GET'])
def setcurentdb():
    setdb(request.args.get('dbid'))
    return redirect(url_for('dbmanager'))


@app.route('/dbmanager/editinfo', methods=['POST'])
def editinfo():
    dbid = request.form['dbid']
    host = request.form.get('host')
    user = request.form.get('user')
    password = request.form.get('password')
    description = request.form['description']
    editdbinfo(dbid=dbid, host=host, user=user, password=password, description=description)
    flash('Database information changed', 'info')
    return redirect(url_for('dbmanager'))


@app.route('/dbmanager/newdb', methods=['POST'])
def newdb():
    addorcrdb = request.form.get('addorcrdb')
    dbname = request.form.get('dbname')
    dbtype = request.form.get('dbtype')
    dbdata = {'dbhost': request.form.get('host'),
              'dbuser': request.form.get('user'),
              'dbpassword': request.form.get('password'),
              'dbdescription': request.form.get('description')}
    if dbtype == "mysql":
        if not mysqlsrvexist(host=dbdata['dbhost'], user=dbdata['dbuser'], password=dbdata['dbpassword']):
            flash("Database not added.", "error")
            return redirect(url_for('dbmanager'))
    if addorcrdb == "create":
        if not createdb(dbtype, dbname, dbdata):
            flash("Database not created", "error")
    elif addorcrdb == "add":
        if not adddb(dbtype=dbtype, dbname=dbname, dbhost=dbdata['dbhost'], dbuser=dbdata['dbuser'],
                     dbpassword=dbdata['dbpassword'], dbdescription=dbdata['dbdescription']):
            flash("Database not added.", "error")
    return redirect(url_for('dbmanager'))


@app.route('/dbmanager/deletedb', methods=['POST'])
def deletedb():
    if request.form.get('deldb'):
        deldb(request.form.get('dbid'))
    delfromappdb(request.form.get('dbid'))
    return redirect(url_for('dbmanager'))


@app.route('/impormanager')
def importmanager():
    sources = get_source()
    uploadfiles = get_uploadfiles()
    importfiles = get_importfiles()
    return render_template('importmanager.html', sources=sources, uploadfiles=uploadfiles, importfiles=importfiles, devices=get_devices())

@app.route('/importmanager/adddevice', methods=['POST'])
def adddevice():
    add_device_db(request.form.get('devicename'))
    return redirect(url_for('importmanager'))

@app.route('/importmanager/setsourcedevice', methods=['POST'])
def setsourcedevice():
    source = request.form.get('source')
    devicename = request.form.get('device')
    if devicename:
        conn = sqlite3.connect(os.path.join(app.config['APP_ROOT'], 'appdb.db'))
        cursor = conn.cursor()
        cursor.execute("UPDATE importsource SET device=? WHERE feature=?", (devicename, source))
        conn.commit()
        conn.close()
    return redirect(url_for('importmanager'))

@app.route('/upload', methods=['POST'])
def upload():
    if not os.path.isdir(app.config['UPLOAD_FOLDER']):
        os.mkdir(app.config['UPLOAD_FOLDER'])
    file = request.files["file"]
    if file:
        filename = file.filename
        destination = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if '.' in filename:
            if filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']:
                filelist = os.listdir(app.config['UPLOAD_FOLDER'])
                if filename in filelist:
                    flash("A file named " + filename + " has already been uploaded", "error")
                    return redirect(url_for('importmanager'))
                file.save(destination)
                if add_file_to_appdb(filename):
                    flash('File ' + filename + ' uploaded', 'info')
                else:
                    flash("File not uploaded", "error")
            else:
                flash("File not uploaded", "error")
        else:
            flash("File not uploaded", "error")
    return redirect(url_for('importmanager'))

@app.route('/wimport', methods=['POST'])
def wimport():
    filename = request.form.get('filename')
    accuracy = request.form.get('accuracy')
    device = request.form.get('device')
    feature = request.form.get('feature')
    if device == "None":
        flash("Device not selected", "error")
        return redirect(url_for('importmanager'))
    deviceid = get_device_id(device)
    filetype = request.form.get('filetype')
    if filetype == "csv":
        Thread(target=wigle_csv_import, args=(app, socketio, filename, accuracy, deviceid, feature)).start()
    elif filetype == "sqlite":
        Thread(target=wigle_sqlite_import, args=(app, socketio, filename, accuracy, deviceid, feature)).start()
    return render_template('import.html', filename=filename, filetype=filetype, accuracy=accuracy)
