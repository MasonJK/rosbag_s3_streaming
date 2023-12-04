import boto3
import rosbag
import rospy
import importlib
import io

class BytesIOMode(io.BytesIO):
    def __init__(self, initial_bytes, mode):
        super().__init__(initial_bytes)
        self.mode = mode

class RosbagStreamer():
    def __init__(self, bucket_name, s3_file_key) -> None:
        self.rosbag_file = BytesIOMode(boto3.client('s3').get_object(Bucket=bucket_name, Key=s3_file_key)['Body'].read(), 'rb')
        self.topic_publishers = {}
        try:
            self.bag = rosbag.Bag(self.rosbag_file)
        except Exception as e:
            print(f"Error opening the bag: {e}")
        self.initialize_publishers()

    def create_publisher(self, topic, topic_type):
        topic_type_class, topic_type_name = topic_type.split('/')
        module = importlib.import_module(f"{topic_type_class}.msg")
        return rospy.Publisher(topic, getattr(module, topic_type_name), queue_size=10)

    def initialize_publishers(self):
        try:
            _, topics_tuple = self.bag.get_type_and_topic_info()
            for topic in topics_tuple:
                topic_type = topics_tuple[topic][0]
                print(f'Initializing publisher for topic: {topic} - Type: {topic_type}')
                self.topic_publishers[topic] = self.create_publisher(topic, topic_type)
            print(f"Initialized {len(self.topic_publishers)} publishers.")
        except Exception as e:
            print(f"Error initializing publishers: {e}")

    def stream(self):
        try:
            start_time = None
            for topic, msg, t in self.bag.read_messages():
                if start_time is None:
                    start_time = t
                    last_time = t
                else:
                    delay = (t - last_time).to_sec()
                    if delay > 0:
                        rospy.sleep(delay)
                    last_time = t
                print('1')
                self.topic_publishers[topic].publish(msg)
            
            self.bag.close()
        except Exception as e:
            print(f"Error reading rosbag: {e}")

# Example usage
rospy.init_node("s3_rosbag_streamer")

bucket_name = 'd-apne2-rm01-s3-00'
s3_file_key = 'wm_robot1/2023-11-27/dangerbag1.bag'

test_rosbag = RosbagStreamer(bucket_name, s3_file_key)
test_rosbag.stream()