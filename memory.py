# memory.py

# Stores program data starting at DATA_START and provides word-level
# Load/store operations used by LW, SW, and cache refill
DATA_START = 0x100
WORD_SIZE = 4

class Memory:
    def __init__(self):
        self.mem = {}  # Address to 32-bit word

    def load_data_file(self, filename):
        addr = DATA_START
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.mem[addr] = int(line, 2)
                addr += WORD_SIZE

    def load_word(self, addr):
        return self.mem.get(addr, 0)

    def store_word(self, addr, value):
        self.mem[addr] = value