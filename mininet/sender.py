"""Mininet sender — reliable file transfer over UDP.

Reads a file in fixed-size chunks and sends them over UDP with a
sliding-window protocol.  Each window slot runs its own retransmission
thread.  Implements SYN/SYN-ACK handshake and FIN/FIN-ACK teardown.

Usage:
    python3 mininet_sender.py
"""

import os
import random
import socket
import time
import _thread

from packet import Packet

# ── Configuration ──────────────────────────────────────────────────

REMOTE_IP   = "10.0.0.1"
LOCAL_IP    = "10.0.0.2"
PORT        = 5507
BUFFER_SIZE = 4096
CHUNK_SIZE  = 1024      # bytes of file data per packet
WINDOW_SIZE = 1000      # concurrent in-flight packets
TIMEOUT     = 0.01      # retransmission interval (seconds)
SOURCE_FILE = "sample_100MB.bin"


class Sender:
    """Manages the full lifecycle of a reliable file transfer over UDP."""

    def __init__(self, filepath, remote_addr, local_addr):
        # File state
        self.filepath = filepath
        self.filesize = os.path.getsize(filepath)
        self.file = open(filepath, "rb")
        self.chunks_sent = 0

        # Networking
        self.remote = remote_addr
        self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_recv.bind(local_addr)
        self.send_lock = _thread.allocate_lock()

        # Sequence tracking
        self.base_seq = random.getrandbits(14)
        self.active_threads = 0

        # Window state
        #   packets:            seq_number → Packet (None once ACK'd during drain)
        #   thread_assignments: thread_id  → seq_number currently assigned
        self.packets = {}
        self.thread_assignments = {}

        # Phase-control flags (turned False to signal threads to stop)
        self._handshake_pending = True
        self._transfer_active = True
        self._teardown_pending = True

    # ── Low-level helpers ──────────────────────────────────────

    def _next_seq(self):
        """Return the current base_seq and advance it by one."""
        seq = self.base_seq
        self.base_seq += 1
        return seq

    def _recv_raw(self):
        """Block until a datagram arrives.  Returns raw bytes."""
        data, _ = self.sock_recv.recvfrom(BUFFER_SIZE)
        return data

    def _read_next_chunk(self, seq_number):
        """Read the next file chunk and wrap it in a Packet.

        Returns None (and flips _transfer_active) when the file is exhausted.
        """
        chunk = self.file.read(CHUNK_SIZE)
        if not chunk:
            print("File exhausted")
            self.active_threads -= 1
            self._transfer_active = False
            return None
        self.chunks_sent += 1
        return Packet(seq_number, data=chunk, data_size=CHUNK_SIZE)

    def _retransmit_loop(self, raw_bytes, is_active_fn):
        """Retransmit *raw_bytes* every TIMEOUT while is_active_fn() is True."""
        last_send = time.time()
        while is_active_fn():
            if time.time() - last_send > TIMEOUT:
                self.sock_send.sendto(raw_bytes, self.remote)
                last_send = time.time()

    # ── Phase 1: Handshake ─────────────────────────────────────

    def connect(self):
        """Perform SYN / SYN-ACK handshake.  Returns True on success."""
        syn_pkt = Packet(self._next_seq(), syn=1)
        self.sock_send.sendto(syn_pkt.to_bytes(), self.remote)
        print("SYN sent")

        _thread.start_new_thread(
            self._retransmit_loop,
            (syn_pkt.to_bytes(), lambda: self._handshake_pending),
        )

        seq, syn, fin = Packet.parse_ack(self._recv_raw())
        self._handshake_pending = False
        if syn == 1:
            print("Connection established")
            return True
        print("Connection refused")
        return False

    # ── Phase 2: Data transfer ─────────────────────────────────

    def _sender_thread(self, thread_id):
        """Per-slot loop: retransmit the assigned packet until reassigned or done."""
        while self._transfer_active:
            while self.packets[self.thread_assignments[thread_id]] is not None:
                seq = self.thread_assignments[thread_id]
                self.send_lock.acquire()
                try:
                    self.sock_send.sendto(
                        self.packets[seq].to_bytes(), self.remote
                    )
                except Exception:
                    self.send_lock.release()
                    print(f"Thread {thread_id} ended (send error)")
                    return
                else:
                    self.send_lock.release()
                    time.sleep(TIMEOUT)
        print(f"Thread {thread_id} ended")

    def _spawn_window(self):
        """Fill the initial window: read WINDOW_SIZE chunks and spawn threads."""
        for slot in range(WINDOW_SIZE):
            thread_id = slot + 1
            pkt = self._read_next_chunk(self.base_seq)
            self.active_threads += 1
            self.packets[self.base_seq] = pkt
            self.thread_assignments[thread_id] = self.base_seq
            _thread.start_new_thread(self._sender_thread, (thread_id,))
            self.base_seq += 1
            print(f"Spawned window slot {slot}")

    def _ack_loop(self):
        """Listen for ACKs and slide the window until all threads retire."""
        print("ACK listener started")
        while True:
            seq, syn, fin = Packet.parse_ack(self._recv_raw())

            active_seqs = list(self.thread_assignments.values())
            if seq not in active_seqs:
                continue
            thread_id = active_seqs.index(seq) + 1

            if not self._transfer_active:
                # File exhausted — retire this thread's slot
                self.packets[seq] = None
                self.active_threads -= 1
                print(self.active_threads)
            else:
                # Slide the window: assign the next chunk to this thread
                new_pkt = self._read_next_chunk(self.base_seq)
                self.packets[self.base_seq] = new_pkt
                self.thread_assignments[thread_id] = self.base_seq
                self.base_seq += 1

            if self.active_threads == 0:
                print("All data acknowledged")
                return

    # ── Phase 3: Teardown ──────────────────────────────────────

    def disconnect(self):
        """Perform FIN / FIN-ACK teardown.  Returns True on success."""
        fin_pkt = Packet(self._next_seq(), fin=1)
        self.sock_send.sendto(fin_pkt.to_bytes(), self.remote)

        _thread.start_new_thread(
            self._retransmit_loop,
            (fin_pkt.to_bytes(), lambda: self._teardown_pending),
        )

        seq, syn, fin = Packet.parse_ack(self._recv_raw())
        self._teardown_pending = False
        if fin == 1:
            print("Connection closed")
            return True
        return False

    # ── Run ────────────────────────────────────────────────────

    def run(self):
        """Execute the full transfer: connect → send → disconnect."""
        if not self.connect():
            return

        start = time.time()
        self._spawn_window()
        self._ack_loop()
        elapsed = time.time() - start

        time.sleep(1)

        if self.active_threads == 0:
            self.disconnect()
        else:
            print("ERROR: incorrect connection termination")

        print(f"Transfer time: {elapsed:.3f}s")
        print(f"Chunks sent:   {self.chunks_sent}")


if __name__ == "__main__":
    sender = Sender(
        filepath=SOURCE_FILE,
        remote_addr=(REMOTE_IP, PORT),
        local_addr=(LOCAL_IP, PORT),
    )
    sender.run()
