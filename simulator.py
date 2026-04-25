# simulator.py

from registers import RegisterFile
from memory import Memory

# Holds global CPU state: PC, registers, memory, instruction list, and pipeline stages
class CPUState:
    def __init__(self, instructions, data_file):
        # Program counter (instructions start at 0x00)
        self.pc = 0

        # Instruction list and quick lookup by PC
        self.instructions = instructions
        self.inst_by_pc = {inst.pc: inst for inst in instructions}

        # Registers and memory
        self.regs = RegisterFile()
        self.mem = Memory()
        self.mem.load_data_file(data_file)

        # Caches (attached in main.py)
        self.icache = None
        self.dcache = None

        # Global cycle counter
        self.cycle = 0

        # Pipeline stages (hold instruction objects or None)
        self.IF_stage = None
        self.ID_stage = None
        self.EX_stages = [None] * 5
        self.MEM_stage = None
        self.WB_stage = None

        # Per-instruction stage exit times for output.txt
        self.timeline = {}

        # Global memory stall state (used by caches)
        self.memory_busy_cycles = 0
        self.pending_memory_request = None

    # True if a cache miss is still being serviced
    def memory_is_busy(self):
        return self.memory_busy_cycles > 0

    # Return the instruction at the given PC (or current PC if none)
    def fetch_instruction(self, pc=None):
        if pc is None:
            pc = self.pc
        return self.inst_by_pc.get(pc, None)