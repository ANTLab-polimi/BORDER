"""
Example topology with two containers (d1, d2),
two switches, and one controller:

          - (c)-
         |      |
(d1) - (s1) - (s2) - (d2)
"""
from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel
import argparse
import itertools
import os

PWD = os.getcwd()

IMAGES = {
    "EMQX": "flipperthedog/emqx-ip:latest",
    "VERNEMQ": "francigjeci/vernemq-debian:latest",
    "RABBITMQ": "flipperthedog/rabbitmq_alpine:latest",
    "HIVEMQ": "francigjeci/hivemq:dns-image",
    # "HIVEMQ":      "flipperthedog/hivemq_alpine:latest",
    "MOSQUITTO": "flipperthedog/mosquitto:latest",
    "SUBSCRIBER": "flipperthedog/alpine_client:latest",
    "PUBLiSHER": "flipperthedog/go_publisher:latest",
    "DISTRPLUS": "flipperthedog/mqttplusdistr:latest"

}

message_delay = 1

brokers = []
switches =[]
sub_list = []
pub_list = []

def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT+ distributed test')
    parser.add_argument('-s', '--size', dest='num_broker', default=5,
                            help='number of brokers', type=int)
    parser.add_argument('-l', '--locality', dest='locality', default='TOTAL',
                            help='locality of the clients')
    return parser.parse_args()

def network_topology():
    info('*** Adding docker containers using ubuntu:trusty images\n')
    for index in range(args.num_broker):
        brokers.append(net.addDocker('d{}'.format(1 + index), ip='10.0.0.{}'.format(251 + index),
                                     dimage="flipperthedog/mqttplusdistr:latest",
                                     environment={
                                         "WS_PORT": 8080 + index,
                                         "BROKER_PORT": 1883 + index,
                                         "CLUSTER_SIZE": args.num_broker,
                                         "BROKER_NUM": index,
                                         "IP_ADDR": '10.0.0.{}'.format(251 + index)
                                     }
                                     ))
    info('*** Adding switches\n')
    # s1 = net.addSwitch('s1')
    # s2 = net.addSwitch('s2')
    for index in range(args.num_broker):
        switches.append(net.addSwitch('s{}'.format(1 + index)))
    info('*** Creating links\n')
    for c, s in zip(brokers, switches):
        print(net.addLink(c, s, cls=TCLink, delay='1ms', bw=1))
    for index in range(len(switches)):
        if (index < len(switches) - 1):
            print(net.addLink(switches[index], switches[index + 1]))
    info('*** Creating publishers\n')
    for index in range(len(brokers)):
        pub = net.addDocker('pub{}'.format(index), ip='10.0.0.{}'.format(301+index),
                            dimage=IMAGES["PUBLiSHER"],
                            volumes=[PWD + '/experiments:/go/src/app/experiments'])
        pub_list.append(pub)

    start_publishers()


def start_publishers():
    info('*** Starting publishers\n')

    for index in range(len(pub_list)):
        publisher_cmd = "docker exec -t mn.pub{id_pub} python3 simple_pub.py -h {host} -p {port}".format(
            id_pub = index,
            host='10.0.0.{}'.format(251+index),
            port= '{}'.format(1883+index)
        )
    os.system(publisher_cmd)


def main():
    info('*** Adding controller\n')
    net.addController('c0')

    network_topology()

    info('*** Starting network\n')
    net.start()
    info('*** Testing connectivity\n')
    for couple in itertools.combinations(brokers, 2):
        net.ping([couple[0], couple[1]])
    info('*** Starting CMDs\n')
    for broker in brokers:
        broker.start()
    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()

if __name__ == "__main__":
    setLogLevel('info')

    net = Containernet(controller=Controller)

    args = arg_parse()
    main()
