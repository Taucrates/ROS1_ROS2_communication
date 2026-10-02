import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import roslibpy

class SummitBridge(Node):
    def __init__(self):
        super().__init__('summit_xl_bridge')
        
        # 1. Connect to robot's ROS 1 via WebSockets
        self.get_logger().info("Connecting to robot...")
        self.ros1 = roslibpy.Ros(host='192.168.0.91', port=9090) # host=<ROS1_IP>
        self.ros1.run()
        
        if self.ros1.is_connected:
            self.get_logger().info("Connection established.")
        else:
            self.get_logger().error("Can not connect to the robot")

        # ROS 2 -> ROS 1
        self.ros1_cmd_pub = roslibpy.Topic(self.ros1, '/robot/cmd_vel', 'geometry_msgs/Twist')
        
        self.cmd_sub = self.create_subscription(
            Twist,
            '/cmd_vel/summit_xl',
            self.cmd_callback,
            10
        )

        # ROS 1 -> ROS 2
        # ROS 2 Publisher
        self.ros2_odom_pub = self.create_publisher(Odometry, '/odom/summit_xl', 10)
        
        # ROS 1 Subscriber
        self.ros1_odom_sub = roslibpy.Topic(self.ros1, '/robot/odom', 'nav_msgs/Odometry')
        self.ros1_odom_sub.subscribe(self.odom_callback)

    def cmd_callback(self, msg):
        # Convert ROS 2 Twist message to JSON for ROS 1
        twist_dict = {
            'linear': {'x': msg.linear.x, 'y': msg.linear.y, 'z': msg.linear.z},
            'angular': {'x': msg.angular.x, 'y': msg.angular.y, 'z': msg.angular.z}
        }
        self.ros1_cmd_pub.publish(roslibpy.Message(twist_dict))

    def odom_callback(self, msg_dict):
        # Convert ROS 1 JSON (dictionary) to Odometry message of ROS 2
        try:
            ros2_msg = Odometry()
            
            ros2_msg.header.frame_id = msg_dict['header']['frame_id']
            # IMPORTANT: ROS 1 uses 'secs' and 'nsecs', ROS 2 uses 'sec' and 'nanosec'
            ros2_msg.header.stamp.sec = msg_dict['header']['stamp']['secs']
            ros2_msg.header.stamp.nanosec = msg_dict['header']['stamp']['nsecs']
            
            ros2_msg.child_frame_id = msg_dict['child_frame_id']
            
            ros2_msg.pose.pose.position.x = msg_dict['pose']['pose']['position']['x']
            ros2_msg.pose.pose.position.y = msg_dict['pose']['pose']['position']['y']
            ros2_msg.pose.pose.position.z = msg_dict['pose']['pose']['position']['z']
            
            ros2_msg.pose.pose.orientation.x = msg_dict['pose']['pose']['orientation']['x']
            ros2_msg.pose.pose.orientation.y = msg_dict['pose']['pose']['orientation']['y']
            ros2_msg.pose.pose.orientation.z = msg_dict['pose']['pose']['orientation']['z']
            ros2_msg.pose.pose.orientation.w = msg_dict['pose']['pose']['orientation']['w']
            
            ros2_msg.pose.covariance = msg_dict['pose']['covariance']
            
            ros2_msg.twist.twist.linear.x = msg_dict['twist']['twist']['linear']['x']
            ros2_msg.twist.twist.linear.y = msg_dict['twist']['twist']['linear']['y']
            ros2_msg.twist.twist.linear.z = msg_dict['twist']['twist']['linear']['z']
            
            ros2_msg.twist.twist.angular.x = msg_dict['twist']['twist']['angular']['x']
            ros2_msg.twist.twist.angular.y = msg_dict['twist']['twist']['angular']['y']
            ros2_msg.twist.twist.angular.z = msg_dict['twist']['twist']['angular']['z']
            
            ros2_msg.twist.covariance = msg_dict['twist']['covariance']
            
            # Publish on local ROS2
            self.ros2_odom_pub.publish(ros2_msg)
            
        except KeyError as e:
            self.get_logger().error(f"Error mapping odometry: {e}")

def main(args=None):
    rclpy.init(args=args)
    bridge = SummitBridge()
    try:
        rclpy.spin(bridge)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.ros1_cmd_pub.unadvertise()
        bridge.ros1_odom_sub.unsubscribe()
        bridge.ros1.terminate()
        bridge.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
