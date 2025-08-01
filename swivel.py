import time
import common.yaml_handle as yaml_handle
from common.ros_robot_controller_sdk import Board

board = Board()
def rotateCamera(val,vel=1):
	#vel = speed in seconds
	#angle should be 0-180
	#500 = Full Right
	#1500 = Middle (Home)
	#2500 = Full Leftss
	board.pwm_servo_set_position(vel, [[5,val]])
