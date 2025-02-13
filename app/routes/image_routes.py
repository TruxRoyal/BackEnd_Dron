from flask import Blueprint, jsonify, request
import cv2

image_bp = Blueprint('image', __name__)

@image_bp.route('/process', methods=['POST'])
def process_image():
    return jsonify({"message": "Image processed"})