# Custom UDP FTP

A reliable file transfer protocol built on top of UDP sockets. Implements TCP-like features — connection handshake (SYN/SYN-ACK), sliding window with per-thread retransmission, ACKs, and connection teardown (FIN/FIN-ACK).

See [architecture.md](architecture.md) for a detailed walkthrough with diagrams.

## Project structure

```
Custom_UDP_FTP/
├── sender_v1DEBUG.py      # localhost sender
├── recv_v1DEBUG.py        # localhost receiver
├── mininet/
│   ├── packet.py          # shared packet module
│   ├── sender.py          # mininet sender
│   ├── receiver.py        # mininet receiver
│   └── run_network.py     # mininet topology launcher
├── architecture.md        # architecture & RDT techniques
└── drafts/                # earlier iterations (not functional)
```

## Working files

| Environment | Sender | Receiver | Network | Port |
|---|---|---|---|---|
| Localhost | `sender_v1DEBUG.py` | `recv_v1DEBUG.py` | `127.0.0.x` | 6666 |
| Mininet | `mininet/sender.py` | `mininet/receiver.py` | `10.0.0.x` | 5507 |

## Usage

### Localhost

Start the receiver first, then the sender:

```bash
# Terminal 1 (receiver)
python3 recv_v1DEBUG.py

# Terminal 2 (sender)
python3 sender_v1DEBUG.py
```

### Mininet

#### Prerequisites

Mininet runs on **Linux** only. On macOS/Windows, use a VM (the [official Mininet VM](http://mininet.org/download/) works out of the box).

1. **Install Mininet** (Ubuntu/Debian):

   ```bash
   sudo apt update
   sudo apt install mininet openvswitch-switch
   ```

2. **Install Python 3** (if not already present):

   ```bash
   sudo apt install python3
   ```

3. **Create a test file** (if `sample_100MB.bin` doesn't exist yet):

   ```bash
   dd if=/dev/urandom of=sample_100MB.bin bs=1M count=100
   ```

#### Running

The included `run_network.py` script creates the two-host topology and drops you into the Mininet CLI:

```bash
# Launch the topology (requires root)
sudo python3 mininet/run_network.py

# Inside the Mininet CLI — start receiver on h1, then sender on h2
mininet> h1 python3 mininet/receiver.py &
mininet> h2 python3 mininet/sender.py
```

You can also simulate real network conditions with link parameters:

```bash
# 10 Mbps bandwidth, 20ms delay, 2% packet loss
sudo python3 mininet/run_network.py --bw 10 --delay 20ms --loss 2
```

When done, exit the CLI and clean up:

```bash
mininet> exit
sudo mn -c
```

The sender reads `sample_100MB.bin` and transfers it over UDP. The receiver writes the reassembled output to `rcv1`.

## `drafts/`

Earlier iterations and rough sketches kept for reference. These are **not functional**:

- `Client_v1.py` — initial pseudocode brainstorm
- `reciever_v1.py` — first receiver attempt (broken socket bind, no binary handling)
- `sender_ v2.py` — transitional sender (multiple bugs, never finished)
- `sender_vDEBUG.py` + `recv_vDEBUG.py` — earlier debug pair (works but superseded)
