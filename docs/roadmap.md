# Roadmap and engineering log

| Phase | Exit evidence |
|---|---|
| 0 — Audit | Pinned source review, licenses and integration decision. |
| 1 — Baseline | Original upstream directed tests, independent Antmicro UVM attempt, version inventory, reproducible local launcher and recorded outcomes. |
| 2 — RTL | Finalize the register contract. Verify the standalone SPI engine, then integrate and verify the Wishbone block. Lint project RTL and exercise boundary parameter sets. |
| 3 — UVM | Qualify the SPI VIP in isolation. Add Wishbone agent, virtual sequences, predictor, scoreboard and end-to-end project tests. |
| 4 — SVA and coverage | Enable validated assertions and record reachable functional bins, exclusions and observed hits. |
| 5 — Regression | Add test/seed selection, repeat and parallel execution, suite timeouts, per-test JSON and optional JUnit. Merge supported coverage per build configuration. |
| 6 — Fault injection | Run five isolated mutations, capture the detecting tests and checker outputs, and rerun restored RTL. |
| 7 — Synthesis | Record generic cells and technology mapping where a valid library is available. Measure timing only with a defined technology, constraints and corners. |
| 8 — Presentation | Package diagrams, register and timing references, measured results, bug studies and provenance for local review. |

## 2026-11-10

- Initialized the local repository and audited the five named Git repositories and the arXiv paper. Pinned the three executable inputs used by Phase 1.
- Probed Windows and WSL2 before installing missing Ubuntu tools. Used separate simulator versions to distinguish a distro Verilator limitation from an upstream test failure.
- Captured actual directed, UVM, lint and generic synthesis outcomes in the [baseline record](../reports/baseline/README.md).
- Ran the candidate SPI VIP loopback independently. Recorded its checker failure and the width-handling issues to isolate during qualification.
- Wrote the proposed register, reset and SPI timing contract and the verification matrix for the first implementation slice.
