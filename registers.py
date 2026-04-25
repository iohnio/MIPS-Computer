# registers.py

NUM_REGISTERS = 32

# Stores 32 general-purpose registers and enforces R0 = 0
class RegisterFile:
    def __init__(self):
        self.regs = [0] * NUM_REGISTERS

    # Return the value of register Ri (R0 always reads as 0)
    def read(self, index: int) -> int:
        if not (0 <= index < NUM_REGISTERS):
            raise IndexError(f"Register index out of range: R{index}")
        if index == 0:
            return 0
        return self.regs[index]

    # Write value into Ri; writes to R0 are ignored
    def write(self, index: int, value: int) -> None:
        if not (0 <= index < NUM_REGISTERS):
            raise IndexError(f"Register index out of range: R{index}")
        if index == 0:
            return
        self.regs[index] = value