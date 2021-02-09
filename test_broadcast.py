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
import time
import subprocess
from threading import Thread
from datetime import datetime
import random
from pathlib import Path
import shlex
import subprocess
import pprint as pp
import docker
import math
import sys
import signal
from io import StringIO




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
pub_loc = []
sub_loc = []
dump_pids = []
stats =[]

ops = ['$AVG', '$SUM', '$MIN', '$MAX']

def arg_parse():
    parser = argparse.ArgumentParser(description='MQTT+ distributed test')
    parser.add_argument('-s', '--size', dest='num_broker', default=5,
                            help='number of brokers', type=int)
    parser.add_argument('-l', '--locality', dest='locality', default='TOTAL',
                            help='locality of the clients')
    parser.add_argument('-d', '--distributed', dest='distr', default='true',
                            help='use bridging or not to connect the brokers')
    return parser.parse_args()

def network_topology():
    info('*** Adding docker containers using ubuntu:trusty images\n')
    for index in range(args.num_broker):
        brokers.append(net.addDocker('d{}'.format(1 + index), ip='10.0.0.{}'.format(251 + index),
                                     dimage="leostaglia/mqttplusdistr:latest",
                                     environment={
                                         "WS_PORT": 8080 + index,
                                         "BROKER_PORT": 1883 + index,
                                         "CLUSTER_SIZE": args.num_broker,
                                         "BROKER_NUM": index,
                                         "IP_ADDR": '10.0.0.{}'.format(251 + index),
                                         "DISTRIBUTED_FLAG" : args.distr
                                     }
                                     ))
    info('*** Adding switches\n')

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
        pub = net.addDocker('pub{}'.format(index), ip='10.0.0.{}'.format(151 + index),
                            dimage='leostaglia/simple_pub:latest')
        pub_list.append(pub)
    info('*** Creating subscribers\n')
    for index in range(0, 5):
        sub = net.addDocker('sub{}'.format(index), ip='10.0.0.{}'.format(1 + index),
                            dimage='leostaglia/simple_sub:latest')
        sub_list.append(sub)

    info('*** Connecting publishers\n')
    for index, pub in enumerate(pub_list):
        print(net.addLink(pub, switches[pub_loc[index]]))

    info('*** Connecting subscribers\n')
    for index, sub in enumerate(sub_list):
        print(net.addLink(sub, switches[sub_loc[index]]))

def start_publishers():
    info('*** Starting publishers\n')

    for index in range(len(pub_list)):
        publisher_cmd = "docker exec -t mn.pub{id_pub} python3 simple_pub.py -h {host} -p {port} -t {topic}".format(
            id_pub = index,
            host='10.0.0.{}'.format(251+pub_loc[index]),
            port= '{}'.format(1883+pub_loc[index]),
            topic = 'room/sens{}/temp'.format(index)
        )
        os.system(publisher_cmd)

def start_subscribers():
    info('*** Starting subscribers\n')

    for index in range(len(sub_list)):
        print('Starting the subscribers that will connect to: 10.0.0.{}:{}'.format(251 + sub_loc[index], 1883 + sub_loc[index]))
        publisher_cmd = "docker exec -t mn.sub{id_pub} python simple_sub.py -h {host} -p {port} -t {topic} -i {ind}".format(
            id_pub=index,
            host='10.0.0.{}'.format(251 + sub_loc[index]),
            port='{}'.format(1883 + sub_loc[index]),
            topic='/room/+/temp',
            ind = index
        )
        os.system(publisher_cmd)

def setup_files():
    path = "experiments/{day}/{minute}/{distr}/{local}locality/".format(
        day=START_DAY,
        minute=START_MINUTE,
        distr = args.distr,
        local=loc)
    Path(path).mkdir(parents=True, exist_ok=True)
    stats_pid = start_statistics(path)
    stats.append(stats_pid)
    dump_pids.extend(start_tcpdump(path))

def start_tcpdump(_path):
    _tcp_pid = []
    for b_id in range(0, args.num_broker):
        cmd_tcpdump = "tcpdump -i s{broker_id}-eth1 src 10.0.0.{ip} -w {folder}tcp{broker_id}.pcap -q".format(
            broker_id=b_id+1, ip = 251+b_id, folder=os.path.expanduser(_path))
        _tcp_pid.append(subprocess.Popen(shlex.split(cmd_tcpdump), stderr=subprocess.DEVNULL))

    print("Logging tcpdump...")
    return _tcp_pid


def start_statistics(_path):
    f = open(_path + "/stats.txt", "w")
    cmd_stats = 'exec docker stats --format "{{.ID}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{' \
                '.NetIO}},{{.BlockIO}},{{.PIDs}}"'
    process_stats = subprocess.Popen(cmd_stats, stdout=f, shell=True, preexec_fn=os.setsid)

    print("Logging stats...")
    return process_stats

def simulation_stop():
    print('Simulation stop started\n')
    time.sleep(300)
    print('Stopping simulation\n')
    for sub_id in sub_list:
        ps_cmd = "docker exec -t mn.{} ps | grep python3 | awk '{{print $1}}'".format(sub_id)
        sub_pid = subprocess.getoutput(ps_cmd)
        sub_pid = [int(x) for x in sub_pid.split("\n") if x]
        for pid in sub_pid:
            cmd = "docker exec -t mn.{} kill -2 {}".format(sub_id, int(pid))
            print("-- {}".format(cmd))
            subprocess.getoutput(cmd)
    os.killpg(os.getpgid(stats[0].pid), signal.SIGTERM)
    for pid in dump_pids:
        pid.kill()

    print('Simulation stopped\n')




def main():
    info('*** Adding controller\n')
    net.addController('c0')
    val = random.randint(0, args.num_broker - 1)
    for index in range(args.num_broker):
        if(args.locality == 'TOTAL'):
            pub_loc.append(val)
        elif(args.locality == 'NULL'):
            pub_loc.append(val)
        else:
            val = random.randint(0, args.num_broker - 1)
            pub_loc.append(val)

    for index in range(0, 5):
        if(args.locality == 'TOTAL'):
            sub_loc.append(pub_loc[0])
        elif(args.locality == 'NULL'):
            sub_loc.append(random.choice([
        i for i in range(0, args.num_broker) if i not in pub_loc[index]]))
        else:
            val = random.randint(0, args.num_broker - 1)
            sub_loc.append(val)

    network_topology()

    info('*** Starting network\n')
    net.start()
    info('*** Testing connectivity\n')
    for couple in itertools.combinations(brokers, 2):
        net.ping([couple[0], couple[1]])
    info('*** Starting CMDs\n')
    for broker in brokers:
        broker.start()
    setup_files()
    time.sleep(5.0)
    start_subscribers()
    time.sleep(5.0)
    start_publishers()
    thread = Thread(target=simulation_stop)
    thread.daemon = True
    thread.start()
    info('*** Running CLI\n')
    CLI(net)
    info('*** Stopping network')
    net.stop()



if __name__ == "__main__":
    setLogLevel('info')

    net = Containernet(controller=Controller)
    START_DAY = datetime.now().strftime("%m-%d")
    START_MINUTE = datetime.now().strftime("%H%M%S")
    args = arg_parse()
    loc = args.locality
    main()