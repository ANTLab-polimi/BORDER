import argparse
import time

import paho.mqtt.client as mqtt


def arg_parse():
    parser = argparse.ArgumentParser(description='Locality experiment', add_help=False)
    parser.add_argument('-m', '--messages', dest='num_messages', default=5,
                        help='number of messages to publish', type=int)
    parser.add_argument('-b', '--broker', dest='broker', default='localhost',
                        help='mqtt broker address')
    parser.add_argument('-p', '--port', dest='port', type=int,
                        default=1883, help='mqtt broker port')
    parser.add_argument('-t', '--topic', dest='topic', default='test',
                        help='topic to publish')
    parser.add_argument('--speed', dest='delay', default=1,
                        help='sleep between stuff', type=int)

    return parser.parse_args()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code: " +str(rc))


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    print("Connecting to the broker {} on port {}".format(args.broker, args.port))

    client.connect(args.broker, port=args.port)
    client.loop_start()
    time.sleep(1)

    print("Publishing on topic `{}`...".format(args.topic))
    while True:
        client.publish(args.topic, str(int(round(time.time() * 1000))))
        time.sleep(args.delay)


if __name__ == "__main__":
    args = arg_parse()
    main()
