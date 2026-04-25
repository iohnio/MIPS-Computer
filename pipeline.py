# pipeline.py

import re
from typing import Dict
from parser import parse_register

STAGE_IF = "IF"
STAGE_ID = "ID"
STAGE_EX5 = "EX5"
STAGE_MEM = "MEM"
STAGE_WB = "WB"

# Simulates one pipelined CPU with EX latencies, branches, HLT, and cache stalls
class PipelineEngine:
    def __init__(self, cpu_state):
        self.cpu = cpu_state
        self.done = False

        self.ex_cycles_left: Dict[object, int] = {}
        self.halt_reached_id = False
        self.icache_miss_in_progress = False
        self.dcache_miss_in_progress = False

    def _init_timeline_entry(self, inst):
        if inst not in self.cpu.timeline:
            self.cpu.timeline[inst] = {
                STAGE_IF: None,
                STAGE_ID: None,
                STAGE_EX5: None,
                STAGE_MEM: None,
                STAGE_WB: None,
            }

    def _record_stage_exit(self, inst, stage_name: str, cycle: int):
        self._init_timeline_entry(inst)
        if self.cpu.timeline[inst][stage_name] is None:
            self.cpu.timeline[inst][stage_name] = cycle

    # EX latency
    def _get_ex_cycles(self, inst) -> int:
        op = inst.opcode.upper()

        if op in ["J", "BEQ", "BNE", "LI"]:
            ex = 0
        elif op in ["AND", "OR", "LW", "SW"]:
            ex = 1
        elif op in ["ADD", "ADDI", "SUB", "SUBI"]:
            ex = 2
        elif op in ["MULT", "MULTI"]:
            ex = 4
        elif op in ["DIV", "REM"]:
            ex = 5
        else:
            ex = 1

        return max(ex, 1)

    # Register usage (for hazards)
    def _is_load(self, inst) -> bool:
        return inst.opcode.upper() == "LW"
    # Parse offset(base) memory operand
    def _parse_mem_operand(self, token):
        token = token.strip()
        m = re.match(r"(-?\d+)\((R\d+)\)", token)
        if not m:
            return None, None
        offset = int(m.group(1))
        base_reg = parse_register(m.group(2))
        return offset, base_reg
    # Destination register index for instructions that write a GPR
    def _dest_reg(self, inst):
        op = inst.opcode.upper()
        if op in ["LI", "LW", "ADD", "ADDI", "SUB", "SUBI",
                  "MULT", "MULTI", "DIV", "REM", "AND", "OR"]:
            try:
                return parse_register(inst.args[0])
            except Exception:
                return None
        return None
    # Set of source register indices read by this instruction
    def _source_regs(self, inst):
        op = inst.opcode.upper()
        srcs = set()

        if op in ["ADD", "SUB", "AND", "OR", "MULT", "MULTI", "DIV", "REM"]:
            if len(inst.args) >= 3:
                try:
                    srcs.add(parse_register(inst.args[1]))
                    srcs.add(parse_register(inst.args[2]))
                except Exception:
                    pass

        elif op in ["ADDI", "SUBI"]:
            if len(inst.args) >= 2:
                try:
                    srcs.add(parse_register(inst.args[1]))
                except Exception:
                    pass

        elif op in ["LW", "SW"]:
            if len(inst.args) >= 2:
                _, base = self._parse_mem_operand(inst.args[1])
                if base is not None:
                    srcs.add(base)
            if op == "SW":
                try:
                    srcs.add(parse_register(inst.args[0]))
                except Exception:
                    pass

        elif op in ["BEQ", "BNE"]:
            if len(inst.args) >= 2:
                try:
                    srcs.add(parse_register(inst.args[0]))
                    srcs.add(parse_register(inst.args[1]))
                except Exception:
                    pass

        return srcs

    # Branch / HLT handling
    def _handle_branch_in_ID(self, inst, cycle):
        self._record_stage_exit(inst, STAGE_ID, cycle)

        op = inst.opcode.upper()
        taken = False
        target_pc = inst.target_pc

        if op == "J":
            taken = True
        elif op in ["BEQ", "BNE"]:
            rs = parse_register(inst.args[0])
            rt = parse_register(inst.args[1])
            v1 = self.cpu.regs.read(rs)
            v2 = self.cpu.regs.read(rt)
            taken = (v1 == v2) if op == "BEQ" else (v1 != v2)

        if taken and target_pc is not None:
            self.cpu.pc = target_pc
            self.cpu.IF_stage = None

        self.cpu.ID_stage = None

    def _handle_hlt_in_ID(self, inst, cycle):
        self._record_stage_exit(inst, STAGE_ID, cycle)
        self.cpu.ID_stage = None
        self.cpu.IF_stage = None
        self.halt_reached_id = True

    # One pipeline cycle
    def step_cycle(self):
        if self.done:
            return

        self.cpu.cycle += 1
        cycle = self.cpu.cycle

        # Global memory stall countdown
        if self.cpu.memory_busy_cycles > 0:
            self.cpu.memory_busy_cycles -= 1
            if self.cpu.memory_busy_cycles == 0:
                if self.cpu.pending_memory_request is not None:
                    req_type = self.cpu.pending_memory_request.get("type")
                    if req_type == "I":
                        self.icache_miss_in_progress = False
                    elif req_type == "D":
                        self.dcache_miss_in_progress = False
                self.cpu.pending_memory_request = None

        IF = self.cpu.IF_stage
        ID = self.cpu.ID_stage
        EX5 = self.cpu.EX_stages[4]
        MEM = self.cpu.MEM_stage
        WB = self.cpu.WB_stage

        # EX countdown
        if EX5 is not None:
            if EX5 not in self.ex_cycles_left:
                self.ex_cycles_left[EX5] = self._get_ex_cycles(EX5)
            self.ex_cycles_left[EX5] -= 1

        # Load-use hazard: ID depends on LW in EX5
        stall_for_hazard = False
        if ID is not None and EX5 is not None and self._is_load(EX5):
            dest = self._dest_reg(EX5)
            if dest is not None:
                if dest in self._source_regs(ID):
                    stall_for_hazard = True

        # WB
        if WB is not None:
            self._record_stage_exit(WB, STAGE_WB, cycle)
            self.cpu.WB_stage = None
            WB = None

        # MEM to WB (with D-cache timing)
        if MEM is not None and self.cpu.WB_stage is None:
            stall_for_dcache = False
            op_mem = MEM.opcode.upper()

            if op_mem in ["LW", "SW"] and self.cpu.dcache is not None:
                if self.dcache_miss_in_progress or self.cpu.memory_is_busy():
                    stall_for_dcache = True
                else:
                    if len(MEM.args) >= 2:
                        offset, base_reg = self._parse_mem_operand(MEM.args[1])
                    else:
                        offset, base_reg = (0, None)

                    addr = 0
                    if base_reg is not None:
                        addr = self.cpu.regs.read(base_reg) + offset

                    prev_hits = self.cpu.dcache.hits
                    if op_mem == "LW":
                        _ = self.cpu.dcache.access_read(addr)
                    else:
                        _ = self.cpu.dcache.access_write(addr, 0)

                    if self.cpu.dcache.hits != prev_hits + 1:
                        self.dcache_miss_in_progress = True
                        self.cpu.memory_busy_cycles = 3 * 4
                        self.cpu.pending_memory_request = {
                            "type": "D",
                            "address": addr,
                        }
                        stall_for_dcache = True

            if not stall_for_dcache:
                self._record_stage_exit(MEM, STAGE_MEM, cycle)
                self.cpu.WB_stage = MEM
                WB = MEM
                self.cpu.MEM_stage = None
                MEM = None

        # EX5 to MEM
        if EX5 is not None and self.cpu.MEM_stage is None:
            remaining = self.ex_cycles_left.get(EX5, 0)
            if remaining <= 0:
                self._record_stage_exit(EX5, STAGE_EX5, cycle)
                self.cpu.MEM_stage = EX5
                MEM = EX5
                self.cpu.EX_stages[4] = None
                del self.ex_cycles_left[EX5]
                EX5 = None

        # ID
        if ID is not None:
            op = ID.opcode.upper()

            if op in ["J", "BEQ", "BNE"]:
                self._handle_branch_in_ID(ID, cycle)
                ID = self.cpu.ID_stage

            elif op == "HLT":
                self._handle_hlt_in_ID(ID, cycle)
                ID = self.cpu.ID_stage

            else:
                if (not stall_for_hazard) and self.cpu.EX_stages[4] is None:
                    self._record_stage_exit(ID, STAGE_ID, cycle)
                    self.cpu.EX_stages[4] = ID
                    EX5 = ID
                    self.cpu.ID_stage = None
                    ID = None

        # IF to ID
        IF = self.cpu.IF_stage
        if (not stall_for_hazard) and IF is not None and self.cpu.ID_stage is None:
            self._record_stage_exit(IF, STAGE_IF, cycle)
            self.cpu.ID_stage = IF
            ID = IF
            self.cpu.IF_stage = None
            IF = None

        # Fetch into IF (with I-cache timing)
        if (not self.halt_reached_id) and (not stall_for_hazard) and self.cpu.IF_stage is None:
            if self.icache_miss_in_progress or self.cpu.memory_is_busy():
                pass
            else:
                if self.cpu.icache is None:
                    inst = self.cpu.fetch_instruction(self.cpu.pc)
                    if inst is not None:
                        self.cpu.IF_stage = inst
                        self.cpu.pc += 4
                else:
                    prev_hits = self.cpu.icache.hits
                    _ = self.cpu.icache.access_read(self.cpu.pc)

                    if self.cpu.icache.hits == prev_hits + 1:
                        inst = self.cpu.fetch_instruction(self.cpu.pc)
                        if inst is not None:
                            self.cpu.IF_stage = inst
                            self.cpu.pc += 4
                    else:
                        self.icache_miss_in_progress = True
                        self.cpu.memory_busy_cycles = 3 * 4
                        self.cpu.pending_memory_request = {
                            "type": "I",
                            "address": self.cpu.pc,
                        }
        # Termination check
        no_more_to_fetch = (
            self.cpu.fetch_instruction(self.cpu.pc) is None
        ) or self.halt_reached_id

        pipeline_empty = (
            self.cpu.IF_stage is None
            and self.cpu.ID_stage is None
            and self.cpu.EX_stages[4] is None
            and self.cpu.MEM_stage is None
            and self.cpu.WB_stage is None
        )

        if no_more_to_fetch and pipeline_empty:
            self.done = True

    def run(self, max_cycles: int = 500):
        while not self.done and self.cpu.cycle < max_cycles:
            self.step_cycle()