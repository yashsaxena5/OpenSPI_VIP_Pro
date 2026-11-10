# Toolchain

Use WSL2 Ubuntu or Linux. From Windows PowerShell, `wsl.exe -d Ubuntu -- make doctor` runs the inventory from the current checkout. Use `make doctor` from a WSL shell. The launcher uses Python's standard library.

## Observed environment

WSL2 Ubuntu 26.04.1 LTS, kernel `6.18.33.2-microsoft-standard-WSL2`. The initial Windows inventory found Git `2.56.0.windows.2`, Python `3.13.14`, Icarus `12.0 (devel) (s20150603-1539-g2693dd32b)` and a GTKWave executable on PATH. Windows tools were excluded from simulation. WSL already had Git, Python, Make and G++. Only missing packages were added in Ubuntu. Package installation reported zero upgrades and zero removals.

| Tool | WSL version used or probed |
|---|---|
| Git | 2.53.0 |
| GNU Make | 4.4.1 |
| GCC C++ | 15.2.0, Ubuntu build `15.2.0-16ubuntu1` |
| Python | 3.14.4 |
| Icarus and VVP | 12.0 stable, Ubuntu package `12.0-3` |
| Verilator | 5.032, Ubuntu package `5.032-1`, and source-built 5.054 at `bbb60a403932a9f695cb6ff001ceb73de6ad9234` |
| Yosys | 0.52, `fee39a3284c90249e1d9684cf6944ffbbcbb8f90` |
| Z3 | 4.13.3, 64-bit |
| GTKWave | 3.3.126 |

## Reproduce on Ubuntu

Check the inventory first and install the tools you are missing. This is the dependency set for this project and the source build.

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends git make g++ perl python3 iverilog \
  yosys z3 gtkwave autoconf bison flex libfl-dev help2man
```

Build Verilator on the Linux filesystem. The exact revision below is the commit behind `v5.054`. The launcher prefers that cached build and accepts an explicit executable via `VERILATOR`.

```sh
cache="${XDG_CACHE_HOME:-$HOME/.cache}/openspi-vip-pro"
mkdir -p "$cache"
git clone --depth 1 --branch v5.054 https://github.com/verilator/verilator.git \
  "$cache/verilator-v5.054"
(
  cd "$cache/verilator-v5.054" || exit 1
  test "$(git rev-parse HEAD)" = bbb60a403932a9f695cb6ff001ceb73de6ad9234 || exit 1
  autoconf && ./configure && make -j8
)
make doctor
make regress
```

On constrained hosts reduce `make -j8` and run `python3 scripts/baseline.py test-uvm --jobs 2`. Verilator also needs an accessible Z3 executable for constrained randomization. A custom binary can be selected with `VERILATOR=/path/to/verilator make test-uvm`. The compatibility failure can be reproduced with `VERILATOR=/usr/bin/verilator make test-uvm` where that executable is 5.032. [Verilator build documentation](https://verilator.org/guide/latest/install.html)

Git needs network access to fetch the exact locked commits on each run. Work directories and generated models live under `$XDG_CACHE_HOME/openspi-vip-pro/runs/` or `~/.cache/openspi-vip-pro/runs/`. Logs and `results.json` land in the corresponding `build/baseline/run-*` directory in the checkout. Both paths are printed. The baseline runner time-limits builds and simulations and propagates failures to Make.
