import os
import uuid
from flask import Flask, request, send_from_directory, jsonify
from io import BytesIO

app = Flask(__name__)

# Absolute path for the uploads directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return "Welcome to the Image Upload API!", 200

@app.route('/health', methods=['GET'])
def health_check():
    return "Healthy!", 200

@app.route('/upload_image', methods=['POST'])
def upload_image():
    # Get the image content (binary data) from the request
    image_content = request.data  # This will get the raw binary data sent in the request

    # Generate a unique filename to avoid conflicts
    image_filename = f"{uuid.uuid4()}.jpg"

    # Save the image to the temporary uploads directory
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    with open(image_path, 'wb') as img_file:
        img_file.write(image_content)

    # Generate the URL to access the image
    image_url = f"/uploads/{image_filename}"

    # Return the URL as a response
    return jsonify({"image_url": image_url})

@app.route('/uploads/<filename>')
def serve_uploaded_image(filename):
    return send_from_directory(os.path.abspath(app.config['UPLOAD_FOLDER']), filename)

if __name__ == '__main__':
    # port = int(os.environ.get("PORT", 5000))  # auto detect Render port
    app.run(host="0.0.0.0", port=5000, debug=True)
