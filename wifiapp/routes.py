from wifiapp import app
from flask import render_template, request, jsonify
from wifiapp.getdbinfo import apmarkers, apinfo, locationinfo

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