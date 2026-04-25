# parser.py

import re

# Represents one parsed instruction and its associated metadata
class Instruction:
    def __init__(self, pc, opcode, args, raw_line, label = None):
        self.pc = pc              
        self.opcode = opcode      
        self.args = args         
        self.raw_line = raw_line  
        self.label = label        
        self.target_pc = None

# Matches register tokens and extracts the number
REGISTER_PATTERN = re.compile(r"R(\d+)")

# Convert a register token into an integer index
def parse_register(token):
    match = REGISTER_PATTERN.fullmatch(token)
    if not match:
        raise ValueError(f"Invalid register: '{token}'")
    return int(match.group(1))

# Parse an immediate value in decimal or hexadecimal form
def parse_immediate(token):
    token = token.strip().lower()

    if token.endswith("h"):
        return int(token[:-1], 16)
    if token.startswith("0x"):
        return int(token, 16)
    return int(token)

# Strip comments/whitespace and split out an optional label
def parse_instruction_line(line):
    line = line.split("#")[0].strip()
    if not line:
        return None, ""

    if ":" in line:
        parts = line.split(":")
        label = parts[0].strip().upper()
        rest = ":".join(parts[1:]).strip()
        return label, rest

    return None, line

# Split opcode and operands from a line of text
def tokenize_instruction(instr_text):
    instr_text = instr_text.upper()
    parts = instr_text.split()
    if not parts:
        return None, []

    opcode = parts[0]
    operand_text = " ".join(parts[1:])
    operands = [t.strip() for t in operand_text.split(",")] if operand_text else []
    return opcode, operands

# Parse inst.txt into Instruction objects and label to PC map
def parse_file(filename):
    instructions = []
    labels = {}

    with open(filename, "r") as f:
        lines = f.readlines()

    pc = 0

    # Pass 1: build instructions and label table
    for line_num, raw in enumerate(lines, start=1):
        label, instr_text = parse_instruction_line(raw)

        if label:
            if label in labels:
                raise ValueError(f"Duplicate label '{label}' on line {line_num}")
            labels[label] = pc

        if instr_text == "":
            continue

        opcode, operands = tokenize_instruction(instr_text)
        if opcode is None:
            continue

        inst = Instruction(
            pc=pc,
            opcode=opcode,
            args=operands,
            raw_line=instr_text,
            label=label,
        )
        instructions.append(inst)
        pc += 4  # One word per instruction

    # Pass 2: resolve branch/jump targets
    for inst in instructions:
        if inst.opcode in ["J", "BNE", "BEQ"]:
            label_token = inst.args[-1]
            if label_token not in labels:
                raise ValueError(f"Undefined label '{label_token}' used in branch/jump")
            inst.target_pc = labels[label_token]

    return instructions, labels