#!/usr/bin/env python3

# app.py
#
# A simple Flask web server that streams video from a USB webcam.
#
# Dependencies:
#   - Flask: A micro web framework for Python.
#   - OpenCV: A library for computer vision tasks.
#
# To install dependencies:
#   pip install Flask opencv-python-headless
#
# To run the server:
#   python3 app.py
#
# Then, open a web browser on any device on the same network and navigate to:
#   http://<your_raspberry_pi_ip>:5000

from flask import Flask, render_template_string, Response
import cv2

# --- Configuration ---
# You might need to change the camera index if you have multiple cameras.
# 0 is usually the default built-in camera, and 1 or higher might be your USB webcam.
# Based on your /dev/video0, index 0 should be correct.
CAMERA_INDEX = 0 
# Host on all available network interfaces
HOST = '0.0.0.0'
PORT = 5000


# --- Flask App Initialization ---
app = Flask(__name__)

# --- Video Capture ---
# Initialize the video capture object. 
# Using cv2.CAP_V4L2 might improve performance on Linux systems like Raspberry Pi.
video_capture = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)

if not video_capture.isOpened():
    # This is a critical error, so we raise an exception.
    raise IOError(f"Cannot open webcam at index {CAMERA_INDEX}. Is it connected and not in use by another application?")

def generate_frames():
    """
    A generator function that continuously captures frames from the webcam,
    encodes them as JPEG, and yields them for streaming.
    """
    while True:
        # Read a frame from the webcam
        success, frame = video_capture.read()
        if not success:
            # If a frame cannot be read, break the loop.
            # This might happen if the camera is disconnected.
            print("Failed to grab frame. Check camera connection.")
            break
        else:
            # Encode the frame in JPEG format
            # The .tobytes() method converts the encoded image to a byte string.
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                # If encoding fails, skip this frame.
                print("Failed to encode frame.")
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield the frame in the format required for multipart streaming
            # The boundary 'frame' is used by the client to separate images.
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# --- Web Page Template ---
# A simple, self-contained HTML page that displays the video stream.
# It uses Tailwind CSS for basic styling and is mobile-responsive.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspberry Pi - Live Webcam Stream</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
    </style>
</head>
<body class="bg-gray-900 text-white flex flex-col items-center justify-center min-h-screen p-4">

    <div class="w-full max-w-4xl mx-auto">
        <h1 class="text-3xl md:text-4xl font-bold text-center mb-2 text-cyan-400">Live Webcam Stream</h1>
        <p class="text-center text-gray-400 mb-6">Streaming from Raspberry Pi 5</p>

        <div class="bg-gray-800 rounded-2xl shadow-2xl overflow-hidden border-4 border-gray-700">
            <!-- The video stream is displayed in this img tag -->
            <img src="{{ url_for('video_feed') }}" alt="Live Video Feed" class="w-full h-full object-cover">
        </div>
        
        <div class="text-center mt-6 text-gray-500 text-sm">
            <p>Server is running on {{ host }}:{{ port }}</p>
            <p>To view this page, access this IP from any device on your local network.</p>
        </div>
    </div>

</body>
</html>
"""

# --- Flask Routes ---
@app.route('/')
def index():
    """
    Serves the main HTML page.
    """
    # render_template_string allows us to use a string as a template
    # and pass variables to it, like the host and port.
    return render_template_string(HTML_TEMPLATE, host=HOST, port=PORT)

@app.route('/video_feed')
def video_feed():
    """
    This route streams the video frames.
    It returns a special Response object with a 'multipart/x-mixed-replace'
    mimetype, which tells the browser to expect a stream of images.
    """
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Main Execution ---
if __name__ == '__main__':
    print(f"Starting server... Access at http://<your_pi_ip>:{PORT}")
    # The 'threaded=True' argument allows Flask to handle multiple requests,
    # which is useful for streaming.
    app.run(host=HOST, port=PORT, threaded=True)

# --- Cleanup ---
# When the script is stopped (e.g., with Ctrl+C), release the camera.
video_capture.release()

