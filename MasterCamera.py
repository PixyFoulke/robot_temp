import cv2
import sys
import Camera 
import asyncio
import socket

def get_ip_address():
    """Gets the local IP address of the machine."""
    s = None
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a remote server (doesn't send data)
        # This helps determine the primary network interface
        s.connect(("8.8.8.8", 80))
        # Get the socket's own address
        ip_address = s.getsockname()[0]
    except Exception as e:
        print(f"Could not get IP address: {e}")
        ip_address = "127.0.0.1" # Fallback to loopback address
    finally:
        if s:
            s.close()
    return ip_address

# Set the variable to your IP address
my_ip = get_ip_address()



print(f"My IP address is: {my_ip}")
def cameraConnection():
    my_camera = Camera()
    my_camera.camera_open()
    while True:
        img = my_camera.frame
        if img is not None:
            cv2.imshow('img', img)
            key = cv2.waitKey(1)
            if key == 27:
                break
    my_camera.camera_close()
    cv2.destroyAllWindows()
def display_network_stream():
    """
    Connects to a network video stream and displays it in a window.
    """
    # --- IMPORTANT ---
    # Replace this with the actual IP address of your streaming device.
    STREAMING_DEVICE_IP = get_ip_address()
    stream_url = f"http://{STREAMING_DEVICE_IP}:8080/?action=stream"

    print(f"Attempting to connect to stream at: {stream_url}")

    # Attempt to open the network video stream.
    cap = cv2.VideoCapture(stream_url)

    # Check if the stream was opened successfully.
    if not cap.isOpened():
        print("Error: Could not open the network video stream.")
        print("Please check the following:")
        print(f"1. Is a streaming service running on the device?")
        print(f"2. Is the IP address '{STREAMING_DEVICE_IP}' correct?")
        print("3. Are your PC and the device on the same network?")
        sys.exit()

    print("Successfully connected to stream. Press 'q' to quit.")

    # Loop to continuously get frames from the stream.
    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()

        # if frame is read correctly ret is True
        if not ret:
            print("Error: Can't receive frame (stream end?). Exiting ...")
            break

        # Display the resulting frame in a window named 'Camera Feed'.
        cv2.imshow('Camera Feed', frame)

        # Wait for the 'q' key to be pressed to exit the loop.
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("'q' pressed, closing the window.")
            break

    # When everything is done, release the capture object and close all windows.
    cap.release()
    cv2.destroyAllWindows()
    print("Stream released and windows closed.")

if __name__ == '__main__':
    try:
        connection = False
        my_camera = Camera.Camera()
        my_camera.camera_open()
        while True:
            img = my_camera.frame
            if img is not None:
                cv2.imshow('img', img)
                key = cv2.waitKey(1)
                if key == 27:
                    break
            if connection == False:
                display_network_stream()
                    
        my_camera.camera_close()
        cv2.destroyAllWindows()
    except Exception as e:
     print(e)
	
	