# OpenSPI-VIP Pro

OpenSPI-VIP Pro is a SystemVerilog SPI host and verification project for a Wishbone B4 Classic peripheral. The Phase 1 checkout contains reproducible upstream baselines and a proposed controller specification. Project RTL and the project UVM environment are scheduled for subsequent phases.

Original project contributions use [Apache-2.0](LICENSE).

## Run the baselines

In WSL2 Ubuntu or Linux, from this checkout:

```sh
make doctor
make test-rtl
make test-uvm
make regress
make lint
make synth
```

`test-rtl` runs the original SPI top, master, and slave benches with Icarus. `test-uvm` compiles and runs Antmicro's UVM example with pinned Accellera UVM. The two suites exercise different designs. `regress` runs both and returns nonzero if either fails. The launcher fetches exact source revisions into isolated Linux work directories. It writes commands, logs, and JSON results under `build/baseline/`.

`lint` keeps the upstream warnings fatal. `synth` reports generic cell counts for the upstream loopback top. `coverage` reports the current phase boundary and exits with code 2. See the [toolchain guide](docs/toolchain.md) for the source-built Verilator required for the observed UVM result.

## Project records

- [Baseline results and evidence](reports/baseline/README.md)
- [Upstream audit and selection](docs/upstream_audit.md)
- [Proposed architecture and register map](docs/architecture.md)
- [Verification plan and coverage matrix](docs/verification_plan.md)
- [Roadmap and engineering log](docs/roadmap.md)
- [Third-party notices](THIRD_PARTY_NOTICES)
