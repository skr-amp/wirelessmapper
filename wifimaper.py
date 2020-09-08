from wifiapp import app
from wifiapp import socketio

if __name__ == '__main__':
    socketio.run(app, debug=True)