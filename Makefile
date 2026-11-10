.DEFAULT_GOAL := help
PYTHON ?= python3

.PHONY: help doctor lint test-rtl test-uvm regress coverage synth
help:
	@printf '%s\n' 'Phase 1 targets (Linux or WSL2)' \
	  '  doctor    Inventory EDA tools' \
	  '  test-rtl  Run the three upstream SPI benches' \
	  '  test-uvm  Run the independent Antmicro UVM example' \
	  '  regress   Run both simulation baselines' \
	  '  lint      Lint the upstream SPI top with Verilator' \
	  '  synth     Synthesize the upstream SPI top into generic cells' \
	  '  coverage  Explain the Phase 1 coverage status'

doctor lint test-rtl test-uvm regress synth:
	$(PYTHON) scripts/baseline.py $@

coverage:
	@printf '%s\n' 'Coverage is scheduled for Phase 4. Phase 1 has no project coverage model.' >&2
	@exit 2
