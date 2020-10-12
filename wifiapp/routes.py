from wifiapp import app
from flask import render_template, request
from wifiapp.getdbinfo import apmarkers

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/getapmarkers', methods=['GET'])
def getapmarkers():
    return apmarkers(request.args.get('bounds'))