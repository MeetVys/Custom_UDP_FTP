"""Mininet receiver — reliable file transfer over UDP.

Listens for incoming packets, sends ACKs, and reassembles the file
in sequence-number order after the connection is closed.

Usage:
    python3 mininet_receiver.py
"""

import socket

from packet import Packet

# ── Configuration ──────────────────────────────────────────────────

REMOTE_IP   = "10.0.0.2"
LOCAL_IP    = "10.0.0.1"
PORT        = 5507
BUFFER_SIZE = 4096
OUTPUT_FILE = "rcv1"


class Receiver:
    """Receives packets, sends ACKs, and writes the reassembled file."""

    def __init__(self, output_path, remote_addr, local_addr):
        self.output_path = output_path
        self.remote = remote_addr

        # Networking
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv.bind(local_addr)
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Reassembly state
        self.received_data = {}     # (seq - base_seq) → raw bytes
        self.base_seq = 0
        self.chunks_received = 0

    # ── Helpers ────────────────────────────────────────────────

    def _send_ack(self, seq, syn=0, fin=0):
        """Send an ACK packet back to the sender."""
        ack = Packet(seq, syn=syn, fin=fin)
        self.sock_send.sendto(ack.to_ack_bytes(), self.remote)

    # ── Main receive loop ──────────────────────────────────────

    def listen(self):
        """Handle incoming packets: SYN → data → FIN."""
        while True:
            raw, _ = self.sock_recv.recvfrom(BUFFER_SIZE)
            seq, syn, fin, payload = Packet.parse_data_packet(raw)

            if syn == 1:
                print("Connection establishing")
                self.base_seq = seq
                self._send_ack(seq, syn=1)

            elif fin == 1:
                print("Connection ending")
                self._send_ack(seq, fin=1)
                return

            else:
                self._send_ack(seq)
                offset = seq - self.base_seq
                if offset not in self.received_data:
                    self.chunks_received += 1
                    self.received_data[offset] = payload

    # ── File reassembly ────────────────────────────────────────

    def write_file(self):
        """Write received chunks to disk in sequence-number order."""
        with open(self.output_path, "wb") as f:
            for key in sorted(self.received_data):
                f.write(self.received_data[key])
        print(f"File written to {self.output_path}")

    # ── Run ────────────────────────────────────────────────────

    def run(self):
        """Execute the full receive: listen → write."""
        self.listen()
        print(f"Chunks received: {self.chunks_received}")
        self.write_file()


if __name__ == "__main__":
    receiver = Receiver(
        output_path=OUTPUT_FILE,
        remote_addr=(REMOTE_IP, PORT),
        local_addr=(LOCAL_IP, PORT),
    )
    receiver.run()
