"""Custom packet format for the UDP file transfer protocol.

Shared between sender and receiver. Two wire formats exist:

  Sender → Receiver (data / control):
      seq:<n>:size:<n>:syn:<0|1>:fin:<0|1>:data:<binary payload>

  Receiver → Sender (ACKs):
      seq:<n>:syn:<0|1>:fin:<0|1>
"""


class Packet:
    """A protocol packet with header fields and an optional binary payload."""

    def __init__(self, seq_number, syn=0, fin=0, data=None, data_size=0):
        self.seq_number = seq_number
        self.syn = syn
        self.fin = fin
        self.data = data
        self.data_size = data_size

    # ── Serialization ──────────────────────────────────────────

    def to_bytes(self):
        """Serialize as a full sender packet (header + binary payload)."""
        header = (
            f"seq:{self.seq_number}:size:{self.data_size}"
            f":syn:{self.syn}:fin:{self.fin}:data:"
        ).encode()
        if self.data is not None:
            return header + self.data
        return header

    def to_ack_bytes(self):
        """Serialize as a lightweight ACK (no size / data fields)."""
        return f"seq:{self.seq_number}:syn:{self.syn}:fin:{self.fin}".encode()

    # ── Deserialization ────────────────────────────────────────

    @staticmethod
    def parse_ack(raw_bytes):
        """Parse a receiver ACK.  Returns (seq, syn, fin)."""
        fields = raw_bytes.decode().split(":")
        return int(fields[1]), int(fields[3]), int(fields[5])

    @staticmethod
    def parse_data_packet(raw_bytes):
        """Parse a sender data packet.  Returns (seq, syn, fin, payload)."""
        fields = raw_bytes.decode("latin-1").split(":")
        seq = int(fields[1])
        syn = int(fields[5])
        fin = int(fields[7])
        header_length = sum(len(fields[i]) for i in range(9)) + 9
        payload = raw_bytes[header_length:]
        return seq, syn, fin, payload
