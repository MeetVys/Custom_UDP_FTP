"""Mininet topology for the UDP file transfer demo.

Creates two hosts connected through a single switch, then drops into
the Mininet CLI so you can launch the sender and receiver manually.

Usage (requires root):
    sudo python3 mininet/run_network.py

Optional link parameters:
    sudo python3 mininet/run_network.py --delay 10ms --loss 1 --bw 10
"""

import argparse

from mininet.net import Mininet
from mininet.node import OVSSwitch, Controller
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel


class TransferTopo(Topo):
    """Single switch connecting two hosts.

        h1 (10.0.0.1, receiver) ──┐
                                   ├── s1
        h2 (10.0.0.2, sender)  ──┘
    """

    def build(self, **link_opts):
        switch = self.addSwitch("s1")
        h1 = self.addHost("h1", ip="10.0.0.1/24")
        h2 = self.addHost("h2", ip="10.0.0.2/24")
        self.addLink(h1, switch, **link_opts)
        self.addLink(h2, switch, **link_opts)


def main():
    parser = argparse.ArgumentParser(description="Launch Mininet for UDP FTP demo")
    parser.add_argument("--bw", type=int, default=None, help="Link bandwidth in Mbps")
    parser.add_argument("--delay", type=str, default=None, help="Link delay (e.g. '10ms')")
    parser.add_argument("--loss", type=float, default=None, help="Packet loss percentage (e.g. 1 for 1%%)")
    args = parser.parse_args()

    link_opts = {}
    if args.bw is not None:
        link_opts["bw"] = args.bw
    if args.delay is not None:
        link_opts["delay"] = args.delay
    if args.loss is not None:
        link_opts["loss"] = args.loss

    setLogLevel("info")
    topo = TransferTopo(**link_opts)
    net = Mininet(topo=topo, link=TCLink, switch=OVSSwitch, controller=Controller)
    net.start()

    print("\n========================================")
    print("  Topology ready")
    print("  h1 (10.0.0.1) = receiver")
    print("  h2 (10.0.0.2) = sender")
    print("========================================")
    print("  Quick start:")
    print("    mininet> h1 python3 mininet/receiver.py &")
    print("    mininet> h2 python3 mininet/sender.py")
    print("========================================")
    if link_opts:
        print(f"  Link config: {link_opts}")
        print("========================================")
    print()

    CLI(net)
    net.stop()


if __name__ == "__main__":
    main()
