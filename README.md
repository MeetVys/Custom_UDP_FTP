# Custom UDP FTP

A reliable file transfer protocol built on top of UDP sockets. Implements TCP-like features — connection handshake (SYN/SYN-ACK), sliding window with per-thread retransmission, ACKs, and connection teardown (FIN/FIN-ACK).

## Working files

| Sender | Receiver | Environment | Port |
|---|---|---|---|
| `sender_v1DEBUG.py` | `recv_v1DEBUG.py` | Localhost (`127.0.0.x`) | 6666 |
| `sender_v1DEBUG_vim.py` | `recv_v1DEBUG vim.py` | Mininet (`10.0.0.x`) | 5507 |

### Usage

Start the receiver first, then the sender:

```bash
# Terminal 1 (receiver)
python3 recv_v1DEBUG.py

# Terminal 2 (sender)
python3 sender_v1DEBUG.py
```

The sender reads `CS3543_100MB` and transfers it over UDP. The receiver writes the reassembled output to `rcv1`.

## `drafts/`

Earlier iterations and rough sketches kept for reference. These are **not functional**:

- `Client_v1.py` — initial pseudocode brainstorm
- `reciever_v1.py` — first receiver attempt (broken socket bind, no binary handling)
- `sender_ v2.py` — transitional sender (multiple bugs, never finished)
- `sender_vDEBUG.py` + `recv_vDEBUG.py` — earlier debug pair (works but superseded by the v1DEBUG pair)
