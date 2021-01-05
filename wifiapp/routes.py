from wifiapp import app
from flask import render_template, request, jsonify, redirect, url_for, flash
from wifiapp.getdbinfo import apmarkers, apinfo, locationinfo
from wifiapp.dbmanager import dblist, setdb, editdbinfo, mysqlsrvexist, createdb, adddb

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
    dbdata = {}
    dbdata['dbhost'] = request.form.get('host')
    dbdata['dbuser'] = request.form.get('user')
    dbdata['dbpassword'] = request.form.get('password')
    dbdata['dbdescription'] = request.form.get('description')
    if dbtype == "mysql":
        if not mysqlsrvexist(host=dbdata['dbhost'], user=dbdata['dbuser'], password=dbdata['dbpassword']):
            flash("Database not added." , "error")
            return redirect(url_for('dbmanager'))
    if addorcrdb == "create":
        if createdb(dbtype, dbname, dbdata):
            flash("Database created", "info")
        else:
            flash("Database not created", "error")
    elif addorcrdb == "add":
        if adddb(dbtype=dbtype, dbname=dbname, dbhost=dbdata['dbhost'], dbuser=dbdata['dbuser'], dbpassword=dbdata['dbpassword'], dbdescription=dbdata['dbdescription']):
            flash("Database added.", "info")
        else:
            flash("Database not added.", "error")
    return redirect(url_for('dbmanager'))

