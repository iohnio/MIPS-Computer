# main.py

import sys
from parser import parse_file
from simulator import CPUState
from cache import InstructionCache, DataCache
from pipeline import PipelineEngine

# Write final timing table and cache info to output_path
def write_output(cpu, instructions, labels, output_path):
    with open(output_path, "w") as f:

        f.write("Cycle Number for Each Stage      IF     ID     EX5    MEM    WB\n")

        for inst in instructions:
            times = cpu.timeline.get(inst, {})
            op = inst.raw_line

            label_for_pc = None
            for lbl, addr in labels.items():
                if addr == inst.pc:
                    label_for_pc = lbl
                    break

            if label_for_pc is not None:
                op = f"{label_for_pc}:   {op}"

            IF  = times.get("IF",  "")
            ID  = times.get("ID",  "")
            EX5 = times.get("EX5", "")
            MEM = times.get("MEM", "")
            WB  = times.get("WB",  "")

            def fmt(x):
                return str(x) if x not in [None, ""] else " "

            if op.split()[0].endswith(":"):
                display = op
            else:
                display = "        " + op

            f.write(
                f"{display:30s}  {fmt(IF):>3}    {fmt(ID):>3}    {fmt(EX5):>3}    {fmt(MEM):>3}    {fmt(WB):>3}\n"
            )

        f.write(f"Total number of access requests for instruction cache: {cpu.icache.accesses}\n")
        f.write(f"Number of instruction cache hits: {cpu.icache.hits}\n")
        f.write(f"Total number of access requests for data cache: {cpu.dcache.accesses}\n")
        f.write(f"Number of data cache hits: {cpu.dcache.hits}\n")


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 main.py inst.txt data.txt output.txt")
        return

    inst_file = sys.argv[1]
    data_file = sys.argv[2]
    out_file = sys.argv[3]

    try:
        instructions, labels = parse_file(inst_file)
    except Exception as e:
        print("Parser error:", e)
        return

    cpu = CPUState(instructions, data_file)
    cpu.icache = InstructionCache(cpu.mem)
    cpu.dcache = DataCache(cpu.mem)

    engine = PipelineEngine(cpu)
    engine.run(max_cycles=10000)

    write_output(cpu, instructions, labels, out_file)


if __name__ == "__main__":
    main()