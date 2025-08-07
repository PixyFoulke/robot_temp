#!/usr/bin/env python3
from flask import Flask, render_template, Response, request, jsonify
import cv2
import time
import threading
import mechanum
import swivel
import lampControl
from Camera import Camera # Using the dedicated Camera class

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Robot State (Thread-Safe) ---
# A dictionary to hold the robot's current state. This is safer for threading.
robot_state = {
    'speed_percent': 50,
    'horizontal_swivel_angle': 1500, # Added a specific key for horizontal swivel
    'vertical_swivel_angle': 1500,   # Initial angle for the vertical swivel servo
    'movement_command': 'stop',      # e.g., 'forward', 'turn_left', 'stop'
    'gimbal_command': 'stop',        # e.g., 'left', 'right', 'stop'
    'lamp_on': False
}
# A lock to ensure that the state is accessed by only one thread at a time.
state_lock = threading.Lock()

# --- Camera Initialization ---
# Create an instance of the Camera class and open the camera
my_camera = Camera()
my_camera.camera_open()
# Allow some time for the camera to initialize properly
time.sleep(1.0)

def robot_control_loop():
    """
    A background thread that continuously checks the robot's state
    and sends the appropriate commands to the hardware.
    """
    global robot_state
    while True:
        with state_lock:
            # Copy state to local variables to minimize time inside the lock
            speed = robot_state['speed_percent']
            movement_cmd = robot_state['movement_command']
            gimbal_cmd = robot_state['gimbal_command']
            horizontal_angle = robot_state['horizontal_swivel_angle']
            vertical_angle = robot_state['vertical_swivel_angle']

        # --- Motor Control ---
        fb_velocity = mechanum.sepVel(speed) or 0
        lr_velocity = (-0.0528 * speed ** 2) + (9.16 * speed) - 46

        if movement_cmd == 'forward':
            mechanum.moveForward(fb_velocity)
        elif movement_cmd == 'backward':
            mechanum.moveBackward(fb_velocity)
        elif movement_cmd == 'left':
            mechanum.moveLeft(lr_velocity)
        elif movement_cmd == 'right':
            mechanum.moveRight(lr_velocity)
        elif movement_cmd == 'turn_left':
            mechanum.turn(-2) # Using a fixed turn speed for simplicity
        elif movement_cmd == 'turn_right':
            mechanum.turn(2)  # Using a fixed turn speed
        elif movement_cmd == 'stop':
            mechanum.stop()

        # --- Gimbal Control (Continuous) for Horizontal Swivel ---
        new_horizontal_angle = horizontal_angle
        if gimbal_cmd == 'left':
            new_horizontal_angle += 50  # Increment for movement
        elif gimbal_cmd == 'right':
            new_horizontal_angle -= 50

        # Clamp the angle to the valid range [500, 2500]
        new_horizontal_angle = max(500, min(2500, new_horizontal_angle))

        # Only send command if the angle has changed
        if new_horizontal_angle != horizontal_angle:
            swivel.rotateCamera(new_horizontal_angle, 0.1) # Faster update time
            with state_lock:
                robot_state['horizontal_swivel_angle'] = new_horizontal_angle

        # --- Loop Delay ---
        time.sleep(0.05) # Loop runs ~20 times per second

# --- Web Page Route ---
@app.route('/')
def index():
    """Renders the main control page from the template file."""
    return render_template('index.html')

# --- Video Streaming ---
def gen_frames():
    """
    A generator function that captures frames from the camera, encodes them,
    and yields them for the video stream.
    """
    while True:
        frame = my_camera.frame
        if frame is None:
            time.sleep(0.1) # Wait a bit if no frame is available
            continue
        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            print("Failed to encode frame")
            continue
        frame_bytes = buffer.tobytes()
        # Yield the frame in the format required for multipart streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Returns the streaming response."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Robot Command Endpoint ---
@app.route('/command', methods=['POST'])
def send_robot_command():
    """
    Receives and processes a command for the robot. This is the main API for
    the web UI to control the robot's state.
    """
    global robot_state
    data = request.get_json()
    command = data.get('command')
    value = data.get('value')
    
    with state_lock:
        if command == 'speed':
            robot_state['speed_percent'] = int(value)
        elif command == 'light':
            if value == 'on':
                lampControl.turn_on()
                robot_state['lamp_on'] = True
            elif value == 'off':
                lampControl.turn_off()
                robot_state['lamp_on'] = False
        elif command == 'movement':
            robot_state['movement_command'] = value
        elif command == 'gimbal':
             robot_state['gimbal_command'] = value

    # For debugging: print the updated state
    print(f"Updated state with: {command}={value} -> New state: {robot_state}")
    return jsonify(status="success", state=robot_state)

@app.route('/swivel_command', methods=['POST'])
def update_swivel():
    """
    Receives and processes a command for the camera swivel servos.
    """
    global robot_state
    data = request.get_json()
    servo_id = data.get('servo')
    angle = int(data.get('angle'))
    
    with state_lock:
        if servo_id == '5': # This is the horizontal servo
            robot_state['horizontal_swivel_angle'] = angle
            swivel.rotateCamera(angle)
            print(f"Set horizontal servo (5) to {angle}")
        elif servo_id == '3': # This is the vertical servo
            robot_state['vertical_swivel_angle'] = angle
            swivel.rotateCameraVert(angle)
            print(f"Set vertical servo (3) to {angle}")
    
    return jsonify(status="success", state=robot_state)

@app.route('/update_speed', methods=['POST'])
def update_speed():
    """Calculates and returns RPM and FPS based on speed percentage."""
    data = request.get_json()
    speed_percent = int(data.get('speed'))
    
    # Safely get velocities
    fb_velocity = mechanum.sepVel(speed_percent)
    if fb_velocity is None: 
        fb_velocity = 0
    
    # Calculate RPM and Feet Per Second
    rpm = mechanum.getRPM(fb_velocity)
    fps = fb_velocity / 304.8  # Convert mm/s to ft/s

    return jsonify(rpm=rpm, fps=fps)

# --- Main Execution ---
if __name__ == '__main__':
    try:
        # Start the background control loop as a daemon thread
        control_thread = threading.Thread(target=robot_control_loop, daemon=True)
        control_thread.start()
        print("🤖 Robot control thread started.")
        # Run the Flask web server
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Clean up resources
        my_camera.camera_release()
        print("Camera released.")
