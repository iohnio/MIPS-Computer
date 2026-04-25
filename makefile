# CMSC 411, Fall 2025, Term project Makefile

PYTHON = python3
MAIN   = main.py
INST   = inst.txt
DATA   = data.txt
OUT    = output.txt

all:
	$(PYTHON) $(MAIN) $(INST) $(DATA) $(OUT)

clean:
	rm -f output.txt
	rm -f *.pyc
	rm -rf __pycache__