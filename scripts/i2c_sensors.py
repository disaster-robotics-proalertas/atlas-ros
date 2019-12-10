#!/usr/bin/env python

import rospy
import rosparam
import signal
import sys

from atlas_ros.msg import Ph, Conductivity, DissolvedOxygen, Temperature, OxiRedoxPotential
from sensor_msgs.msg import TimeReference

from I2Cbus import I2Cbus

# I2C bus global instance
bus = I2Cbus()

# Custom function to get parameters with default values
# For some reason, this version of rosparam is behaving
# weirdly about default values
def get_param(name, default=''):
	if rospy.has_param(name):
		return get_param(name)
	else:
		return default

def handle_sigint(sig, frame):
	"""
	Handles SIGINT signal (CTRL+C interruption)
	"""
	rospy.loginfo("[atlas_node] Shutting down")
	rospy.signal_shutdown('SIGINT received (CTRL+C)')
	sys.exit(0)

def node():
	# Initialize ROS node
	rospy.init_node('atlas_node', anonymous=True)

	# Get parameters for topics
	phTopic = get_param('/atlas/pH/topic', '/atlas/raw/pH')
	orpTopic = get_param('/atlas/RedoxPotential/topic', '/atlas/raw/RedoxPotential')
	doTopic = get_param('/atlas/DissolvedOxygen/topic', '/atlas/raw/DissolvedOxygen')
	ecTopic = get_param('/atlas/Conductivity/topic', '/atlas/raw/Conductivity')
	tempTopic = get_param('/atlas/Temperature/topic', '/atlas/raw/Temperature')

	# Publishers
	phPub = rospy.Publisher(phTopic, Ph, queue_size=10)
	orpPub = rospy.Publisher(orpTopic, OxiRedoxPotential, queue_size=10)
	doPub = rospy.Publisher(doTopic, DissolvedOxygen, queue_size=10)
	ecPub = rospy.Publisher(ecTopic, Conductivity, queue_size=10)
	tempPub = rospy.Publisher(tempTopic, Temperature, queue_size=10)

	# Wait for GPST
	rospy.loginfo("[atlas_node] Waiting for GPS time...")
	gpst_topic = get_param('/atlas/gpst/topic', '/time_reference')
	rospy.wait_for_message(gpst_topic, TimeReference)
	rospy.loginfo("[atlas_node] Done")

	# Topic info
	rospy.loginfo("[atlas_node] Publishing pH information in %s topic" % phTopic)
	rospy.loginfo("[atlas_node] Publishing Redox Potential information in %s topic" % orpTopic)
	rospy.loginfo("[atlas_node] Publishing Dissolved Oxygen information in %s topic" % doTopic)
	rospy.loginfo("[atlas_node] Publishing Conductivity information in %s topic" % ecTopic)
	rospy.loginfo("[atlas_node] Publishing Temperature information in %s topic" % tempTopic)

	# Message instances for sensors
	pH_msg = Ph()
	pH_msg.header.frame_id = 'atlaspi'
	ec_msg = Conductivity()
	ec_msg.header.frame_id = 'atlaspi'
	do_msg = DissolvedOxygen()
	do_msg.header.frame_id = 'atlaspi'
	temp_msg = Temperature()
	temp_msg.header.frame_id = 'atlaspi'
	orp_msg = OxiRedoxPotential()
	orp_msg.header.frame_id = 'atlaspi'

	# Rate (defined by parameter)
	hz = get_param('/atlas/rate', "10")
	rate = rospy.Rate(int(hz))

	port = ''
	# Run while ROS is active
	while not rospy.is_shutdown():
		##### Get data from Conductivity sensor and publish it
		# Get port from ec port parameter
		address = get_param('/atlas/Conductivity/SEPort', '1')

		# Get EC sensor data and publish it
		gpst_msg = rospy.wait_for_message(gpst_topic, TimeReference)
		ec_msg.gpst = gpst_msg.time_ref
		ec_msg.header.stamp = rospy.Time.now()
		data = bus.get_data(address).split(',')
		ec_msg.ec = float(data[0])
		ec_msg.ppm = int(data[1])
		ec_msg.salinity = float(data[2])
		ec_msg.specificGrav = float(data[3])
		ecPub.publish(ec_msg)

		##### Get data from RedoxPotential sensor and publish it
		# Get port from redox port parameter
		address = get_param('/atlas/RedoxPotential/SEPort', '2')

		# Get Redox Potential sensor data and publish it
		gpst_msg = rospy.wait_for_message(gpst_topic, TimeReference)
		orp_msg.gpst = gpst_msg.time_ref
		orp_msg.header.stamp = rospy.Time.now()
		orp_msg.orp = float(bus.get_data(address))
		orpPub.publish(orp_msg)

		##### Get data from pH sensor and publish it
		# Get port from ph port parameter
		address = get_param('/atlas/pH/SEPort', '3')

		# Get ph sensor data and publish it
		gpst_msg = rospy.wait_for_message(gpst_topic, TimeReference)
		pH_msg.gpst = gpst_msg.time_ref
		pH_msg.header.stamp = rospy.Time.now()
		pH_msg.pH = float(bus.get_data(address))
		phPub.publish(pH_msg)

		##### Get data from DissolvedOxygen sensor and publish it
		# Get port from ec port parameter
		address = get_param('/atlas/DissolvedOxygen/SEPort', '4')

		# Get dissolved oxygen sensor data and publish it
		gpst_msg = rospy.wait_for_message(gpst_topic, TimeReference)
		do_msg.gpst = gpst_msg.time_ref
		do_msg.header.stamp = rospy.Time.now()
		do_msg.do = float(bus.get_data(address))
		doPub.publish(do_msg)

		##### Get data from Temperature sensor and publish it
		# Get port from ec port parameter
		address = get_param('/atlas/Temperature/SEPort', '5')

		# Get RTD sensor data and publish it
		gpst_msg = rospy.wait_for_message(gpst_topic, TimeReference)
		temp_msg.gpst = gpst_msg.time_ref
		temp_msg.header.stamp = rospy.Time.now()
		temp_msg.celsius = float(bus.get_data(address))
		temp_msg.fahrenheit = temp_msg.celsius*1.8 + 32.0	# Conversion to Fahrenheit
		tempPub.publish(temp_msg)

		# Sleep
		rate.sleep()

if __name__ == "__main__":
	signal.signal(signal.SIGINT, handle_sigint)
	node()
