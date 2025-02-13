from flask import jsonify

def handle_bad_request(error):
    return jsonify({"error": "Bad request"}), 400

def handle_not_found(error):
    return jsonify({"error": "Not found"}), 404

def handle_internal_error(error):
    return jsonify({"error": "Internal server error"}), 500