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
setLogLevel('info')

net = Containernet(controller=Controller)
info('*** Adding controller\n')
net.addController('c0')
info('*** Adding docker containers using ubuntu:trusty images\n')
d1 = net.addDocker('d1', ip='10.0.0.251', dimage="flipperthedog/mqttplusdistr:latest",
                   environment={
                       "WS_PORT": 8080,
                       "BROKER_PORT": 1883,
                       "CLUSTER_SIZE": 2,
                       "BROKER_NUM": 0,
                       "IP_ADDR": '10.0.0.251'
                   }
                   )
d2 = net.addDocker('d2', ip='10.0.0.252', dimage="flipperthedog/mqttplusdistr:latest",
                   environment={
                       "WS_PORT": 8081,
                       "BROKER_PORT": 1884,
                       "CLUSTER_SIZE": 2,
                       "BROKER_NUM": 1,
                       "IP_ADDR": '10.0.0.252'
                   })
info('*** Adding switches\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')
info('*** Creating links\n')
net.addLink(d1, s1)
net.addLink(s1, s2, cls=TCLink, delay='1ms', bw=1)
net.addLink(s2, d2)
info('*** Starting network\n')
net.start()
info('*** Testing connectivity\n')
net.ping([d1, d2])
info('*** Starting CMDs\n')
d1.start()
d2.start()
info('*** Running CLI\n')
CLI(net)
info('*** Stopping network')
net.stop()