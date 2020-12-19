from wifiapp import app
from flask import render_template, request, jsonify, redirect, url_for
from wifiapp.getdbinfo import apmarkers, apinfo, locationinfo
from wifiapp.dbmanager import dblist, setdb, editdbinfo

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
    return redirect(url_for('dbmanager'))


