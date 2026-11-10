# Phase 1 baseline results

Run on 2026-11-10 in WSL2 Ubuntu 26.04.1 LTS. The source revisions are pinned in the [baseline lock](../../third_party/baseline.lock.json). See the [toolchain inventory](../../docs/toolchain.md) for exact versions and [observed output](observed.txt) for command and diagnostic excerpts.

| Case | Tool | Result | Observed evidence |
|---|---|---|---|
| Original `make sim` / `tb_spi_top` | Icarus 12.0 | PASS | 3,049 checks passed, 0 failed. |
| Original `tb_spi_master` | Icarus 12.0 | PASS | 30,052 checks passed, 0 failed. |
| Original `tb_spi_slave` | Icarus 12.0 | PASS | 30,055 checks passed, 0 failed. |
| Antmicro `sig_model_test` | Verilator 5.032, UVM 2020.3.1 | FAIL, compile | `PKGNODECL` in `uvm_coreservice.svh:379`, exit 1. No simulation binary. |
| Antmicro `sig_model_test`, seed 1 | Verilator 5.054, UVM 2020.3.1 | PASS | 10 matching scoreboard comparisons, 2 UVM warnings, 0 errors, 0 fatals. |
| Candidate `spi_loopback_test`, seed 1 | Verilator 5.054, UVM 2020.3.1 | FAIL, simulation | Mode 0, 0/20 checks passed, 29 UVM errors, 0 fatals. Process exit 0. |
| Upstream `spi_top` strict lint | Verilator 5.032 and 5.054 | FAIL, lint | Three `WIDTHEXPAND` warnings on both. Only 5.032 reports the additional `UNOPTFLAT` path through the slave edge decode. |
| Upstream `spi_master`, width 1 | Icarus 12.0 | FAIL, elaboration | The two RX part selects become `[-1:0]` and `[0:1]`. |
| Upstream `spi_top`, generic synthesis | Yosys 0.52 | PASS | `check -assert` found zero problems. 356 generic cells across the default width-8, divider-8 hierarchy. |

Each directed count is the upstream bench's count of individual checks. All three use their default random generator behavior and instantiate the corresponding immediate assertion module. Icarus reports that it includes all bits in the sensitivity of `always_comb` blocks with constant selects. All three simulations completed with their pass summaries and no recorded assertion errors.

The two Antmicro builds use identical SystemVerilog source, UVM and test settings. Verilator 5.032 stops at the `uvm_phase_hopper::type_id::create` reference. Switching to source-built 5.054 resolves that compiler blocker. The launcher follows the upstream `UVM_NO_DPI` and `-Wno-fatal` settings and explicitly enables assertions. The build log retains 32 width diagnostics from the upstream UVM field automation expansion and example expressions. Runtime warnings concern DPI-based test-name handling and component-name checks. The selected test ran via `+UVM_TESTNAME=sig_model_test` and the log recorded all ten comparisons.

The generic synthesis count is a tool- and configuration-specific structural estimate. The upstream fixed Sky130 Liberty path was absent and OpenSTA was unavailable in WSL. The baseline supplies no mapped area, path delays, setup or hold results. Project RTL, SVA coverage and the project UVM regression are later milestones.

## Reproduction

```sh
make doctor
make test-rtl
VERILATOR=/usr/bin/verilator make test-uvm  # on the observed 5.032 installation
make test-uvm                              # selects the source-built 5.054 when present
make regress
make lint
make synth
```

The observed combined run is `build/baseline/run-odiamjo1/`. The 5.032 UVM failure is in `run-5o7fdyup`, the 5.032 lint failure in `run-f0hzilrp`, the 5.054 lint failure in `run-545y57lg`, and the synthesis log in `run-iy1tvtje`. These local run directories contain full commands, raw logs and JSON outcomes. The checked-in excerpts omit local path prefixes. To reproduce the width-1 probe, enter the pinned `spi-sv-core` checkout and run `iverilog -g2012 -s spi_master -Pspi_master.DATA_WIDTH=1 -tnull rtl/spi_master.sv`.

### Separate SPI VIP probe

Run the following from the root of the [pinned candidate checkout](https://github.com/mikaildemirtas4-hue/spi-uart-uvm-vip/tree/733b00e26bf921afde544dcf0a942101b4d6665f). Set `uvm_src` to the absolute path of the pinned UVM `src` directory fetched by the Antmicro run.

```sh
verilator="${XDG_CACHE_HOME:-$HOME/.cache}/openspi-vip-pro/verilator-v5.054/bin/verilator"
obj=$(mktemp -d)
timeout 240 "$verilator" --binary -j 4 --timing --assert -Wno-fatal --top-module tb_top \
  --Mdir "$obj" +define+UVM_NO_DPI "+incdir+$uvm_src" +incdir+spi_vip +incdir+spi_vip/example \
  "$uvm_src/uvm_pkg.sv" spi_vip/spi_if.sv spi_vip/spi_vip_pkg.sv \
  spi_vip/example/spi_example_pkg.sv spi_vip/example/tb_top.sv > vip-build.log 2>&1 &&
timeout 30 "$obj/Vtb_top" +UVM_TESTNAME=spi_loopback_test +verilator+seed+1 > vip-run.log 2>&1
```

Inspect `Checker totals` and the UVM error and fatal counts. The model can finish with exit 0 after UVM errors. The build retained 153 width diagnostics from UVM macro expansion and example expressions. Local raw logs are `build/baseline/spi-vip-loopback-build.log` and `spi-vip-loopback-run.log`. This standalone experiment is outside `make regress`, which runs the pinned SPI RTL and Antmicro baselines.
