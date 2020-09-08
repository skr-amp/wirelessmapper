from flask import Flask
from config import Config
from flask_socketio import SocketIO, send

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
app.config.from_object(Config)

from wifiapp import routes