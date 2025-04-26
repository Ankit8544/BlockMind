import os
import uuid
from flask import Flask, request, send_from_directory, jsonify
from io import BytesIO

app = Flask(__name__)

# Directory where the images will be temporarily stored
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Set the folder for serving static files (images)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# This route will handle the upload and return the URL of the image
@app.route('/upload_image', methods=['POST'])
def upload_image():
    # Get the image content (binary data) from the request
    image_content = request.files['image'].read()  # This is 'response.content'

    # Generate a unique filename to avoid conflicts
    image_filename = f"{uuid.uuid4()}.jpg"

    # Save the image to the temporary uploads directory
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    with open(image_path, 'wb') as img_file:
        img_file.write(image_content)

    # Generate the URL to access the image
    # Assuming the app is deployed and publicly accessible
    image_url = f"/static/{image_filename}"

    # Return the URL as a response
    return jsonify({"image_url": image_url})

# This route serves the uploaded images
@app.route('/static/<filename>')
def serve_image(filename):
    # Serve the image from the 'uploads' directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
