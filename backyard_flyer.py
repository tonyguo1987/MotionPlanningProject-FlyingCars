import argparse
import time
from enum import Enum

import numpy as np

from udacidrone import Drone
from udacidrone.connection import MavlinkConnection, WebSocketConnection  # noqa: F401
from udacidrone.messaging import MsgID


class States(Enum):
    MANUAL = 0
    ARMING = 1
    TAKEOFF = 2
    WAYPOINT = 3
    LANDING = 4
    DISARMING = 5


class BackyardFlyer(Drone):

    def __init__(self, connection):
        super().__init__(connection)
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.all_waypoints = [[0.0, 0.0, 3.0],
                              [20.0, 0.0, 3.0],
                              [20.0, 20.0, 3.0],
                              [0.0, 20.0, 3.0]]
        self.in_mission = True
        self.check_state = {}
        self.THRESHOLD = 0.15
        self.HEADING = 0.05
        self.is_back = False

        # initial state
        self.flight_state = States.MANUAL

        # Register all your callbacks here
        self.register_callback(MsgID.LOCAL_POSITION, self.local_position_callback)
        self.register_callback(MsgID.LOCAL_VELOCITY, self.velocity_callback)
        self.register_callback(MsgID.STATE, self.state_callback)

    def local_position_callback(self):
        """
        This triggers when `MsgID.LOCAL_POSITION` is received and self.local_position contains new data
        """
        if self.flight_state == States.TAKEOFF:
            if -1. * self.local_position[2] > 0.95 * self.target_altitude:
                self.waypoint_transition()
        elif self.flight_state == States.WAYPOINT:
            # If local position has reached the target position
            if abs(self.local_position[0] - self.target_position[0]) < self.THRESHOLD and \
                abs(self.local_position[1] - self.target_position[1]) < self.THRESHOLD:
                # If the quad flys back to the origin
                if self.target_position[0]- self.all_waypoints[0][0]  < self.THRESHOLD and \
                    self.target_position[1]- self.all_waypoints[0][1] < self.THRESHOLD:
                    self.landing_transition()
                    return
                self.waypoint_transition()

    def velocity_callback(self):
        """
        This triggers when `MsgID.LOCAL_VELOCITY` is received and self.local_velocity contains new data
        """
        if self.flight_state == States.LANDING:
            if ((self.global_position[2] - self.global_home[2] < self.THRESHOLD) and
            abs(self.local_position[2]) < 0.05):
                self.disarming_transition()

    def state_callback(self):
        """
        This triggers when `MsgID.STATE` is received and self.armed and self.guided contain new data
        """
        if not self.in_mission:
            return
        if self.flight_state == States.MANUAL:
            self.arming_transition()
        elif self.flight_state == States.ARMING:
            self.takeoff_transition()
        elif self.flight_state == States.DISARMING:
            self.manual_transition()

    def calculate_box(self):
        """
        1. Return waypoints to fly a box
        """
        #return np.array(self.all_waypoints[0])
        for i in range(len(self.all_waypoints)):
            waypoints = self.all_waypoints[i]
            if abs(waypoints[0] - self.target_position[0]) < self.THRESHOLD \
                and abs(waypoints[1] - self.target_position[1]) < self.THRESHOLD:
                print ((i+1) % len(self.all_waypoints))
                return np.array(self.all_waypoints[(i+1) % len(self.all_waypoints)])

    def arming_transition(self):
        """
        1. Take control of the drone
        2. Pass an arming command
        3. Set the home location to current position
        4. Transition to the ARMING state
        """
        self.take_control()
        self.arm()
        self.set_home_position( self.global_position[0],
                                self.global_position[1],
                                self.global_position[2],)
        self.flight_state = States.ARMING
        print("arming transition")

    def takeoff_transition(self):
        """
        1. Set target_position altitude to 3.0m
        2. Command a takeoff to 3.0m
        3. Transition to the TAKEOFF state
        """
        print("takeoff transition")
        self.target_altitude = 3.0
        self.target_position[2] = self.target_altitude
        self.takeoff(self.target_altitude)
        self.flight_state = States.TAKEOFF

    def waypoint_transition(self):
        """
        1. Command the next waypoint position
        2. Transition to WAYPOINT state
        """
        print("waypoint transition")
        waypoint = self.calculate_box()
        self.target_position = waypoint
        print (waypoint)
        #waypoint = [10.0, 0.0, 3.0]
        self.cmd_position(waypoint[0],
                          waypoint[1],
                          waypoint[2],
                          self.HEADING)
        self.flight_state = States.WAYPOINT


    def landing_transition(self):
        """
        1. Command the drone to land
        2. Transition to the LANDING state
        """
        print("landing transition")
        self.land()
        self.flight_state = States.LANDING

    def disarming_transition(self):
        """
        1. Command the drone to disarm
        2. Transition to the DISARMING state
        """
        print("disarm transition")
        self.disarm()
        self.flight_state = States.DISARMING

    def manual_transition(self):
        """This method is provided

        1. Release control of the drone
        2. Stop the connection (and telemetry log)
        3. End the mission
        4. Transition to the MANUAL state
        """
        print("manual transition")

        self.release_control()
        self.stop()
        self.in_mission = False
        self.flight_state = States.MANUAL

    def start(self):
        """This method is provided

        1. Open a log file
        2. Start the drone connection
        3. Close the log file
        """
        print("Creating log file")
        self.start_log("Logs", "NavLog.txt")
        print("starting connection")
        self.connection.start()
        print("Closing log file")
        self.stop_log()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5760, help='Port number')
    parser.add_argument('--host', type=str, default='127.0.0.1', help="host address, i.e. '127.0.0.1'")
    args = parser.parse_args()

    conn = MavlinkConnection('tcp:{0}:{1}'.format(args.host, args.port), threaded=False, PX4=False)
    #conn = WebSocketConnection('ws://{0}:{1}'.format(args.host, args.port))
    drone = BackyardFlyer(conn)
    time.sleep(2)
    drone.start()
