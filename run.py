from flask import Flask, jsonify
from djitellopy import Tello

app = Flask(__name__)

tello = None

def initialize_tello():
    global tello
    if tello is None:
        tello = Tello()
        tello.connect()

initialize_tello() 

@app.route('/battery', methods=['GET'])
def get_battery():
    battery_level = tello.get_battery()
    return jsonify({"battery": battery_level})

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False) 
