from flask import jsonify


def success(message, status_code=200, data=None):
    return jsonify({
        "success": True,
        "message": message,
        "data": data
    }), status_code


def error(message, status_code=500, error=None):
    return  jsonify({
        "success": False,
        "message": message,
        "error": error
    }), status_code