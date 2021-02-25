import os
from wifiapp import app, socketio
from flask import render_template, request, jsonify, redirect, url_for, flash
from threading import Thread
from wifiapp.getdbinfo import apmarkers, apinfo, locationinfo
from wifiapp.dbmanager import dblist, setdb, editdbinfo, mysqlsrvexist, createdb, adddb, deldb, delfromappdb
from wifiapp.wimporter import check_file, get_devices, add_device_db, wigle_csv_import, wigle_sqlite_import


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


@app.route('/upload', methods=['POST'])
def upload():
    target = os.path.join(app.config['APP_ROOT'], 'upload/')
    if not os.path.isdir(target):
        os.mkdir(target)
    file = request.files["file"]
    if file:
        filename = file.filename
        extension = filename.rsplit('.', 1)[1]
        destination = "/".join([target, filename])
        if extension == "csv":
            file.save(destination)
            return redirect(url_for('importer', filename=filename))
        elif extension == "gz" and filename.rsplit('.', 2)[1] == "csv":
            file.save(destination)
            return redirect(url_for('importer', filename=filename))
        elif extension == "sqlite":
            file.save(destination)
            return redirect(url_for('importer', filename=filename))


@app.route('/importer', methods=['GET'])
def importer():
    filename = request.args.get('filename')
    fileinfo = check_file(filename)
    if fileinfo["type"] == "csv" and fileinfo["app"] == "WigleWifi":
        return render_template("wimporter.html", filename=filename, fileinfo=fileinfo, devices=get_devices())
    elif fileinfo["type"] == "sqlite" and fileinfo["app"] == "WigleWifi":
        return render_template("wimporter.html", filename=filename, fileinfo=fileinfo, devices=get_devices())


@app.route('/importer/adddevice', methods=['POST'])
def adddevice():
    add_device_db(request.form.get('devicename'))
    return redirect(url_for('importer', filename=request.form.get('filename')))


@app.route('/wimport', methods=['POST'])
def wimport():
    filename = request.form.get('filename')
    accuracy = request.form.get('accuracy')
    deviceid = int(request.form.get('deviceid'))
    filetype = request.form.get('filetype')
    if filetype == "csv":
        Thread(target=wigle_csv_import, args=(app, socketio, filename, accuracy, deviceid)).start()
    elif filetype == "sqlite":
        Thread(target=wigle_sqlite_import, args=(app, socketio, filename, accuracy, deviceid)).start()
    return render_template('import.html', filename=filename, filetype=filetype, accuracy=accuracy)
