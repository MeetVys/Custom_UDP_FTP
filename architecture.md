# Architecture

## Overview

This project implements a reliable file transfer protocol entirely in the application layer, using raw UDP datagrams as the transport. UDP provides no delivery guarantees, ordering, or congestion control — all of that is built from scratch here using techniques modeled after TCP.

The sender reads a file (`sample_100MB.bin`) in fixed-size chunks, wraps each chunk in a custom packet with a header, and pushes it over a UDP socket. The receiver collects these packets, sends back acknowledgments, and reassembles the file in sequence-number order once the transfer is complete.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HIGH-LEVEL OVERVIEW                         │
│                                                                     │
│  ┌──────────┐     UDP Datagrams      ┌──────────┐    ┌──────────┐  │
│  │ sample   │  ═══════════════════>   │          │    │          │  │
│  │ _100MB   │     (custom packets)   │ Receiver │───>│   rcv1   │  │
│  │ .bin     │                        │          │    │ (output) │  │
│  │ (source) │  <═══════════════════  │          │    │          │  │
│  └────┬─────┘     (ACK packets)      └──────────┘    └──────────┘  │
│       │                                                             │
│       v                                                             │
│  ┌──────────┐                                                       │
│  │  Sender  │                                                       │
│  │ (chunks  │                                                       │
│  │  + sends)│                                                       │
│  └──────────┘                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

Two environment-specific variants exist, tuned for different network conditions.

---

## Environments

### Localhost

```
┌─────────────────────── Same Machine ───────────────────────┐
│                                                             │
│   Sender (127.0.0.2)              Receiver (127.0.0.1)     │
│  ┌─────────────────┐             ┌─────────────────┐       │
│  │ sender_v1DEBUG  │             │ recv_v1DEBUG    │       │
│  │     .py         │◄──────────►│     .py          │       │
│  └─────────────────┘  loopback   └─────────────────┘       │
│                        Port 6666                            │
│                                                             │
│  Window: 200  |  Timeout: 1ms  |  Buffer: 2048B            │
└─────────────────────────────────────────────────────────────┘
```

| Parameter | Value |
|---|---|
| Buffer Size | 2048 bytes |
| Packet Data Size | 1024 bytes |
| Window Size | 200 |
| Retransmit Timeout | 1 ms |

The localhost variant runs both sender and receiver on the same machine using two loopback addresses. Because loopback has virtually zero latency and no packet loss, the window size is kept at 200 and the retransmission timeout is an aggressive 1 ms. This variant is used for functional testing and development.

### Mininet

```
┌──────────────────── Mininet Virtual Network ────────────────────┐
│                                                                  │
│  ┌──────────┐       ┌──────────┐       ┌──────────┐             │
│  │  Host h2 │       │ Virtual  │       │  Host h1 │             │
│  │10.0.0.2  │◄─────►│  Switch  │◄─────►│10.0.0.1  │             │
│  │ (Sender) │       │          │       │(Receiver)│             │
│  └──────────┘       └──────────┘       └──────────┘             │
│       │            Emulated Link            │                    │
│       │          (latency, loss,            │                    │
│       │           bandwidth)                │                    │
│       │                                     │                    │
│  mininet/                             mininet/                   │
│    sender.py            Port 5507       receiver.py              │
│                                                                  │
│  Window: 1000  |  Timeout: 10ms  |  Buffer: 4096B               │
└──────────────────────────────────────────────────────────────────┘
```

| Parameter | Value |
|---|---|
| Buffer Size | 4096 bytes |
| Packet Data Size | 1024 bytes |
| Window Size | 1000 |
| Retransmit Timeout | 10 ms |

The Mininet variant runs on a software-defined virtual network where the sender and receiver are separate virtual hosts connected through emulated links. These links can be configured with realistic latency, bandwidth limits, and packet loss via the included `mininet/run_network.py` topology launcher. To compensate for real network conditions:

- **Window size is 5x larger** (1000 vs 200) to keep the pipe full over higher-latency links.
- **Timeout is 10x longer** (10 ms vs 1 ms) to avoid spurious retransmissions on a slower network.
- **Buffer size is doubled** (4096 vs 2048) to handle larger bursts without dropping packets at the socket level.
- **The sender thread includes a try/except guard** around `sendto()` calls, gracefully handling socket errors that can occur in Mininet's virtual network stack (the localhost version omits this since loopback sockets don't fail).

The Mininet code is structured as a Python package under `mininet/`:

```
mininet/
├── packet.py          Shared Packet class (serialization & parsing)
├── sender.py          Sender class — connect(), _spawn_window(), _ack_loop(), disconnect()
├── receiver.py        Receiver class — listen(), write_file()
└── run_network.py     Mininet topology launcher (--bw, --delay, --loss)
```

`packet.py` provides a single `Packet` class shared by both sender and receiver, handling both wire formats (full data packets and lightweight ACKs). The sender and receiver are each wrapped in a class (`Sender` and `Receiver`) that encapsulates all socket, window, and sequence state.

### Parameter Comparison

```
                    Localhost         Mininet
                ┌──────────────┬──────────────┐
  Window Size   │     200      │    1000      │  ← 5x larger to fill the pipe
                ├──────────────┼──────────────┤
  Timeout       │     1 ms     │    10 ms     │  ← 10x longer for real latency
                ├──────────────┼──────────────┤
  Buffer Size   │   2048 B     │   4096 B     │  ← 2x larger for burst tolerance
                ├──────────────┼──────────────┤
  Port          │    6666      │    5507      │
                ├──────────────┼──────────────┤
  Network       │  Loopback    │  Virtual LAN │
                ├──────────────┼──────────────┤
  Error Guard   │     No       │    Yes       │  ← try/except on sendto()
                └──────────────┴──────────────┘
```

---

## Why UDP — And How the Protocol Runs on Top of It

UDP (`SOCK_DGRAM`) is a minimal transport protocol. It provides:

- Addressing (IP + port)
- A checksum for corruption detection
- Nothing else — no connections, no ordering, no delivery guarantees, no flow control

The project deliberately chooses UDP as the foundation so that every reliability mechanism is implemented explicitly in application code. This is the core educational purpose: to understand what TCP does by rebuilding it piece by piece.

### Dual-Socket Architecture

Both the sender and receiver create two separate UDP sockets — one bound locally for receiving, and one unbound for sending. All communication is stateless from UDP's perspective; the "connection" exists only in the application logic.

```
         SENDER MACHINE                              RECEIVER MACHINE
  ┌───────────────────────┐                    ┌───────────────────────┐
  │                       │                    │                       │
  │  ┌─────────────────┐  │   UDP datagrams    │  ┌─────────────────┐  │
  │  │  sock_send       │──┼──────────────────>──┼──│  sock_recv       │  │
  │  │  (unbound)       │  │   DATA, SYN, FIN  │  │  (bound to       │  │
  │  └─────────────────┘  │                    │  │   LOCAL:PORT)    │  │
  │                       │                    │  └─────────────────┘  │
  │  ┌─────────────────┐  │   UDP datagrams    │  ┌─────────────────┐  │
  │  │  sock_recv       │<─┼──────────────────<──┼──│  sock_send       │  │
  │  │  (bound to       │  │   ACK, SYN-ACK,   │  │  (unbound)       │  │
  │  │   LOCAL:PORT)    │  │   FIN-ACK         │  └─────────────────┘  │
  │  └─────────────────┘  │                    │                       │
  │                       │                    │                       │
  └───────────────────────┘                    └───────────────────────┘
```

### What UDP Gives Us vs. What We Build

```
┌────────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER (this project)               │
│                                                                    │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ ┌─────────┐  │
│  │Connection│ │ Sequence │ │  Sliding  │ │  ACK   │ │  Out-of │  │
│  │Handshake │ │ Numbers  │ │  Window   │ │  Based │ │  Order  │  │
│  │SYN/      │ │ & Order  │ │  + Per-   │ │ Retx   │ │Reassem- │  │
│  │SYN-ACK   │ │          │ │  Thread   │ │        │ │  bly    │  │
│  └──────────┘ └──────────┘ └───────────┘ └────────┘ └─────────┘  │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐   │
│  │Connection Teardown│  │  Custom Packet Format (header+data) │   │
│  │FIN / FIN-ACK      │  │                                      │   │
│  └──────────────────┘  └──────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────────┤
│                     UDP (transport layer)                          │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐                               │
│  │  Addressing  │  │   Checksum   │   That's it. Nothing else.    │
│  │  (IP + Port) │  │  (integrity) │                               │
│  └──────────────┘  └──────────────┘                               │
├────────────────────────────────────────────────────────────────────┤
│                     IP (network layer)                             │
└────────────────────────────────────────────────────────────────────┘
```

---

## Reliable Data Transfer Techniques

### 1. Connection Handshake (SYN / SYN-ACK)

Before any data is sent, the sender initiates a connection using a two-way handshake modeled after TCP's SYN mechanism.

```
      Sender                                        Receiver
        │                                               │
        │  SYN  (syn=1, seq=base)                       │
        │──────────────────────────────────────────────>│
        │                                               │
        │              ┌─────────────────────────┐      │
        │              │ Receiver stores base     │      │
        │              │ seq number for ordering  │      │
        │              └─────────────────────────┘      │
        │                                               │
        │  SYN-ACK  (syn=1, seq=base)                   │
        │<──────────────────────────────────────────────│
        │                                               │
   ┌────┴────┐                                    ┌─────┴─────┐
   │connected│                                    │  ready to │
   │         │                                    │  receive  │
   └─────────┘                                    └───────────┘
```

- The sender generates a random initial sequence number using `random.getrandbits(14)` and sends a packet with the `syn` flag set to `1`.
- The receiver sees `syn=1`, records the sender's base sequence number, and echoes back a SYN-ACK.
- A dedicated **retransmission timer thread** (`_retransmit_loop`) continuously re-sends the SYN packet at the configured timeout interval until the SYN-ACK arrives, at which point the `_handshake_pending` flag is flipped to stop the timer.

**Retransmission on SYN loss:**

```
      Sender                                        Receiver
        │                                               │
        │  SYN  (seq=base)                              │
        │────────────────────── X  (lost!)              │
        │                                               │
        │  ...TIMEOUT expires...                        │
        │                                               │
        │  SYN  (seq=base)  [retransmit]                │
        │──────────────────────────────────────────────>│
        │                                               │
        │  SYN-ACK  (seq=base)                          │
        │<──────────────────────────────────────────────│
        │                                               │
   ┌────┴────┐                                          │
   │connected│  timer exits (_handshake_pending=False)  │
   └─────────┘                                          │
```

### 2. Sequence Numbers

Every packet carries a monotonically increasing sequence number in its header.

```
  File: sample_100MB.bin
  ┌────────┬────────┬────────┬────────┬────────┬─────┐
  │chunk 1 │chunk 2 │chunk 3 │chunk 4 │chunk 5 │ ... │  (1024 bytes each)
  └───┬────┴───┬────┴───┬────┴───┬────┴───┬────┴─────┘
      │        │        │        │        │
      v        v        v        v        v
  seq=base+1  +2       +3       +4       +5
      │        │        │        │        │
      v        v        v        v        v
  ┌────────┬────────┬────────┬────────┬────────┐
  │pkt 101 │pkt 102 │pkt 103 │pkt 104 │pkt 105 │    Packets on the wire
  └────────┴────────┴────────┴────────┴────────┘

  At the receiver, data is keyed by (seq - base):
  ┌──────────────────────────────────────────────┐
  │ received_data = {                             │
  │     1: <bytes from pkt 101>,                 │
  │     2: <bytes from pkt 102>,                 │
  │     4: <bytes from pkt 104>,   ← out of order│
  │     3: <bytes from pkt 103>,   ← arrived late│
  │     5: <bytes from pkt 105>,                 │
  │ }                                            │
  │                                              │
  │ write_file() → sorted keys → correct file    │
  └──────────────────────────────────────────────┘
```

Sequence numbers serve three purposes:

- **Ordering**: The receiver stores data keyed by `(seq_number - base_seq)`, allowing reassembly in the correct order regardless of arrival sequence.
- **Duplicate detection**: If a packet's offset is already in the receiver's `received_data` dictionary, the data is not stored again — only a fresh ACK is sent.
- **ACK matching**: The sender maps sequence numbers to sending threads via `thread_assignments`, so when an ACK arrives, it knows which thread/packet to retire.

### 3. Sliding Window with Per-Thread Retransmission

The sender uses a sliding window protocol to keep multiple packets in flight simultaneously. The implementation is unique — each window slot is assigned its own dedicated thread.

```
  ┌─────────────────────────── SENDER ──────────────────────────────┐
  │                                                                  │
  │  _spawn_window() reads W chunks and spawns W threads:            │
  │                                                                  │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       ┌──────────┐   │
  │  │ Thread 1 │  │ Thread 2 │  │ Thread 3 │  ...  │ Thread W │   │
  │  │ seq=101  │  │ seq=102  │  │ seq=103  │       │ seq=300  │   │
  │  └────┬─────┘  └────┬─────┘  └────┬─────┘       └────┬─────┘   │
  │       │              │              │                   │         │
  │       v              v              v                   v         │
  │  ┌─────────────────────────────────────────────────────────┐     │
  │  │              sock_send  (send_lock protected)           │     │
  │  └──────────────────────────┬──────────────────────────────┘     │
  └─────────────────────────────┼────────────────────────────────────┘
                                │
                    UDP datagrams on the wire
                                │
  ┌─────────────────────────────┼──── RECEIVER ──────────────────────┐
  │                             v                                     │
  │                      sock_recv                                    │
  │                         │                                         │
  │                         v                                         │
  │                  listen() loop                                    │
  │                    │    │    │                                     │
  │                    v    v    v                                     │
  │              ACK  ACK  ACK  ...                                   │
  └───────────────────────────────────────────────────────────────────┘
```

**Each thread's lifecycle — send/sleep/repeat (`_sender_thread`):**

```
  Thread N:
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  while _transfer_active:                                 │
  │    while packets[thread_assignments[N]] is not None:     │
  │      ┌──────────────┐                                    │
  │      │ acquire lock │                                    │
  │      │ send packet  │──────> to receiver                 │
  │      │ release lock │                                    │
  │      └──────┬───────┘                                    │
  │             │                                            │
  │      ┌──────▼───────┐                                    │
  │      │sleep(TIMEOUT)│                                    │
  │      └──────┬───────┘                                    │
  │             │                                            │
  │             └──────> loop back and send again             │
  │                                                          │
  │  When packets[seq] becomes None → thread exits           │
  └──────────────────────────────────────────────────────────┘
```

**Window advancement when an ACK arrives (`_ack_loop`):**

```
  BEFORE ACK for seq=102:
  ┌──────────┬──────────┬──────────┬──────────┐
  │ Thread 1 │ Thread 2 │ Thread 3 │ Thread 4 │
  │ seq=101  │ seq=102  │ seq=103  │ seq=104  │
  │ sending  │ sending  │ sending  │ sending  │
  └──────────┴──────────┴──────────┴──────────┘

  ACK seq=102 arrives → _ack_loop() handles it:
    1. Finds Thread 2 owns seq=102
    2. Reads next chunk from file → new packet seq=105
    3. packets[105] = new_packet
    4. thread_assignments[2] = 105      (reassign Thread 2)

  AFTER:
  ┌──────────┬──────────┬──────────┬──────────┐
  │ Thread 1 │ Thread 2 │ Thread 3 │ Thread 4 │
  │ seq=101  │ seq=105  │ seq=103  │ seq=104  │
  │ sending  │ NEW pkt! │ sending  │ sending  │
  └──────────┴──────────┴──────────┴──────────┘
```

**Key data structures on the sender (`Sender` class):**

```
  packets (seq → Packet):                   thread_assignments (id → seq):
  ┌─────────┬─────────────────┐             ┌───────────┬─────────────┐
  │ seq 101 │ Packet          │             │ Thread 1  │    101      │
  │ seq 102 │ Packet          │             │ Thread 2  │    102      │
  │ seq 103 │ Packet          │             │ Thread 3  │    103      │
  │ seq 104 │ Packet          │             │ Thread 4  │    104      │
  │ ...     │ ...             │             │ ...       │    ...      │
  └─────────┴─────────────────┘             └───────────┴─────────────┘
       │                                          │
       │  When ACK received for seq 102:          │
       │  packets[102] = None (retire)            │  thread_assignments[2] = 105
       │  packets[105] = new_pkt (advance)        │  (reassign thread)
       v                                          v
```

A `send_lock` mutex protects the shared send socket from concurrent thread access.

### 4. Acknowledgments (ACKs)

The receiver sends an ACK for **every** packet it receives, including duplicates. The ACK carries the sequence number of the received packet, allowing the sender to identify exactly which packet was acknowledged.

```
      Sender                                        Receiver
        │                                               │
        │  DATA  (seq=105, data=<1024 bytes>)           │
        │──────────────────────────────────────────────>│
        │                                               │
        │                            ┌─────────────┐    │
        │                            │ if new seq: │    │
        │                            │   store data│    │
        │                            │ else:       │    │
        │                            │   (discard) │    │
        │                            └──────┬──────┘    │
        │                                   │           │
        │  ACK  (seq=105)                   │           │
        │<──────────────────────────────────────────────│
        │                                               │
   ┌────┴─────────────────────┐                         │
   │ recv() matches seq=105   │                         │
   │ to a thread, reassigns   │                         │
   │ it to next file chunk    │                         │
   └──────────────────────────┘                         │
```

This is a **per-packet ACK** scheme (not cumulative). Each ACK retires exactly one packet from the sender's window.

### 5. Timeout-Based Retransmission

Rather than using a single retransmission timer for the whole window, each thread acts as its own retransmission timer.

```
  Thread 3 sending seq=103:

  TIME ──────────────────────────────────────────────────────────>

  ─── send ─── sleep ─── send ─── sleep ─── send ─── sleep ─── send ──
       103    TIMEOUT     103    TIMEOUT     103    TIMEOUT     103
                                                        │
                                                ACK 103 arrives!
                                                Thread reassigned
                                                to seq=108
                                                        │
                                                        v
                                              ─── send ─── sleep ───
                                                   108    TIMEOUT

  If a packet is lost:
  ─── send ──── sleep ──── send ──── sleep ──── send ────
       103     TIMEOUT      103     TIMEOUT      103
        │                    │                    │
        X (lost)             X (lost)             ✓ (delivered!)
                                                  │
                                             ACK arrives → reassign
```

Lost packets are automatically retransmitted without any explicit loss detection logic. The tradeoff is redundant transmissions (packets may be re-sent even after the ACK is in flight), but this is acceptable given the simplicity of the design.

### 6. Out-of-Order Reassembly

The receiver does not require packets to arrive in order.

```
  Packets arrive:    seq=103, seq=101, seq=104, seq=102, seq=105
                         │        │        │        │        │
                         v        v        v        v        v

  received_data dict after all arrivals:
  ┌───────┬──────────────────────────────────┐
  │ key   │ value                            │
  ├───────┼──────────────────────────────────┤
  │   2   │ <1024 bytes from seq 103>        │  arrived 1st
  │   0   │ <1024 bytes from seq 101>        │  arrived 2nd
  │   3   │ <1024 bytes from seq 104>        │  arrived 3rd
  │   1   │ <1024 bytes from seq 102>        │  arrived 4th
  │   4   │ <1024 bytes from seq 105>        │  arrived 5th
  └───────┴──────────────────────────────────┘
         key = (seq_number - base)

  write_file() iterates in sorted key order:
  ┌───────┬──────────────────────────────────┐
  │   0   │ <1024 bytes from seq 101>        │ ──> write first
  │   1   │ <1024 bytes from seq 102>        │ ──> write second
  │   2   │ <1024 bytes from seq 103>        │ ──> write third
  │   3   │ <1024 bytes from seq 104>        │ ──> write fourth
  │   4   │ <1024 bytes from seq 105>        │ ──> write fifth
  └───────┴──────────────────────────────────┘

  Result: rcv1 is byte-identical to the original file
```

### 7. Connection Teardown (FIN / FIN-ACK)

Once all data packets have been acknowledged (`active_threads == 0`), the sender initiates a clean teardown via `disconnect()`:

```
      Sender                                        Receiver
        │                                               │
        │  All threads retired. Begin teardown.         │
        │                                               │
        │  FIN  (fin=1, seq=N)                          │
        │──────────────────────────────────────────────>│
        │                                               │
        │       ┌────────────────────────────────┐      │
        │       │ _retransmit_loop thread starts │      │
        │       │ retransmits FIN on timeout     │      │
        │       └────────────────────────────────┘      │
        │                                               │
        │  FIN-ACK  (fin=1, seq=N)                      │
        │<──────────────────────────────────────────────│
        │                                               │
   ┌────┴────┐    timer stopped                    ┌──────┴──────┐
   │  done   │    (_teardown_pending=False)        │ write_file()│
   └─────────┘                                     │ & exit      │
                                                    └─────────────┘
```

A `_retransmit_loop` thread re-sends the FIN at the timeout interval until the FIN-ACK is received, handling the case where the FIN is lost.

---

## Custom Packet Format

```
  SENDER PACKET (data-carrying):
  ┌─────────────────────── ASCII header ───────────────────────┬──── binary ────┐
  │ seq:<seq_number>:size:<data_size>:syn:<0|1>:fin:<0|1>:data:│<1024 raw bytes>│
  └────────────────────────────────────────────────────────────┴────────────────┘
  │◄──────────────── colon-delimited, encoded as UTF-8 ───────►│◄─ raw bytes ──►│

  Example data packet:
  ┌──────────────────────────────────────────────────────┬──────────────────────┐
  │ seq:4231:size:1024:syn:0:fin:0:data:                 │ \x89\x50\x4e\x47... │
  └──────────────────────────────────────────────────────┴──────────────────────┘

  CONTROL PACKETS (SYN, FIN — no payload):
  ┌──────────────────────────────────────────────────────┐
  │ seq:4230:size:0:syn:1:fin:0:data:                    │   (SYN)
  └──────────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────────┐
  │ seq:4500:size:0:syn:0:fin:1:data:                    │   (FIN)
  └──────────────────────────────────────────────────────┘

  RECEIVER ACK PACKET (lighter format, no size/data fields):
  ┌────────────────────────────────────┐
  │ seq:<seq_number>:syn:0:fin:0       │   (ACK)
  └────────────────────────────────────┘
  ┌────────────────────────────────────┐
  │ seq:<seq_number>:syn:1:fin:0       │   (SYN-ACK)
  └────────────────────────────────────┘
  ┌────────────────────────────────────┐
  │ seq:<seq_number>:syn:0:fin:1       │   (FIN-ACK)
  └────────────────────────────────────┘
```

Both formats are handled by the shared `Packet` class in `mininet/packet.py`. On the sender side, `Packet.to_bytes()` serializes the full header + payload; on the receiver side, `Packet.parse_data_packet()` splits on `:` and calculates the byte offset where the binary data begins to extract the payload without corruption. ACKs use the lighter `to_ack_bytes()` / `parse_ack()` pair.

---

## Complete Transfer Lifecycle

```
      Sender                                        Receiver
        │                                               │
  ══════╪══════════ PHASE 1: HANDSHAKE ═════════════════╪═══════
        │                                               │
        │──── SYN (syn=1, seq=base) ──────────────────>│
        │                                               │
        │<─── SYN-ACK (syn=1, seq=base) ──────────────│
        │                                               │
  ══════╪══════════ PHASE 2: DATA TRANSFER ═════════════╪═══════
        │                                               │
        │  _spawn_window() creates W threads              │
        │  _ack_loop() starts listening                 │
        │                                               │
        │──── DATA (seq=base+1) ──────────────────────>│──ACK──>
        │──── DATA (seq=base+2) ──────────────────────>│──ACK──>
        │──── DATA (seq=base+3) ──────────────────────>│──ACK──>
        │       ...W packets in flight...               │
        │<─── ACK  (seq=base+1) ──────────────────────│
        │  → Thread reassigned to seq=base+W+1          │
        │──── DATA (seq=base+W+1) ────────────────────>│──ACK──>
        │<─── ACK  (seq=base+2) ──────────────────────│
        │  → Thread reassigned to seq=base+W+2          │
        │──── DATA (seq=base+W+2) ────────────────────>│──ACK──>
        │       ...                                     │
        │       ...file chunks continue...              │
        │       ...                                     │
        │  [file exhausted — no more chunks to assign]  │
        │  [threads retire as final ACKs arrive]        │
        │  [active_threads → 0]                         │
        │                                               │
  ══════╪══════════ PHASE 3: TEARDOWN ══════════════════╪═══════
        │                                               │
        │──── FIN (fin=1) [disconnect()] ──────────────>│
        │                                               │
        │<─── FIN-ACK (fin=1) ────────────────────────│
        │                                               │
   ┌────┴────┐                                   ┌──────┴──────┐
   │  DONE   │                                   │ write_file()│
   │ (print  │                                   │ reassemble  │
   │  time)  │                                   │ & save rcv1 │
   └─────────┘                                   └─────────────┘
```
