# MIPS-Computer
## Project Description
MIPS-computer is a Python-based simulator of a simplified pipelined MIPS (Microprocessor without Interlocked Pipeline Stages) architecture that executes a subset of MIPS assembly instructions, including arithmetic, data transfer, and control operations. It models a multi-stage CPU pipeline with data forwarding, hazard handling, and branch prediction, while also simulating an instruction cache and data cache with realistic memory latency and contention. The simulator processes assembly input programs and produces cycle-accurate execution traces along with cache performance statistics, providing insight into processor design and system-level architectural behavior.
## How to Run Project
1. open terminal
2. compile: python3 simulator.py inst.txt data.txt output.txt
3. see output: cat output.txt
## Example Output
<img width="664" height="268" alt="Screenshot 2026-04-25 at 9 53 44 PM" src="https://github.com/user-attachments/assets/b5785f54-4c07-4052-970f-538214745671" />



