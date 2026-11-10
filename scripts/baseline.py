#!/usr/bin/env python3
"""Reproduce the pinned Phase 1 upstream checks on Linux or WSL2."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "openspi-vip-pro"
SOURCE_VERILATOR = CACHE / "verilator-v5.054" / "bin" / "verilator"
TOOLS = {
    "git": ("git", "--version"),
    "make": ("make", "--version"),
    "g++": ("g++", "--version"),
    "python3": ("python3", "--version"),
    "iverilog": ("iverilog", "-V"),
    "vvp": ("vvp", "-V"),
    "yosys": ("yosys", "-V"),
    "z3": ("z3", "--version"),
    "gtkwave": ("gtkwave", "--version"),
}


class BaselineError(Exception):
    """A tool, build, or test failed its baseline gate."""


def verilator():
    default = SOURCE_VERILATOR if SOURCE_VERILATOR.with_name("verilator_bin").is_file() else "verilator"
    return os.environ.get("VERILATOR", str(default))


def run(command, cwd, log, timeout=120):
    command = [str(arg) for arg in command]
    with log.open("a", encoding="utf-8") as output:
        print(f"$ cd {shlex.quote(str(cwd))} && {shlex.join(command)}", file=output, flush=True)
        try:
            with subprocess.Popen(
                command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, start_new_session=True
            ) as process:
                try:
                    status = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    print(f"[wall-clock timeout after {timeout} s]", file=output)
                    status = 124
        except OSError as exc:
            print(exc, file=output)
            status = 127
        print(f"[exit {status}]", file=output)
    if status:
        raise BaselineError(f"exit {status} from {command[0]}; see {log}")
    return log.read_text(encoding="utf-8", errors="replace")


def checkout(name, work, logs):
    lock = json.loads((ROOT / "third_party/baseline.lock.json").read_text(encoding="utf-8"))
    entry = lock[name]
    repo = work / name
    repo.mkdir()
    log = logs / f"fetch-{name}.log"
    run(["git", "init", "--quiet"], repo, log)
    run(["git", "fetch", "--quiet", "--depth=1", entry["url"], entry["commit"]], repo, log)
    run(["git", "-c", "core.autocrlf=false", "checkout", "--quiet", "--detach", entry["commit"]], repo, log)
    return repo


def rtl(repo, bench, log):
    if bench == "top":
        output = run(["make", "sim"], repo, log)
    else:
        top = f"tb_spi_{bench}"
        run(["iverilog", "-g2012", "-s", top, "-o", top, f"rtl/spi_{bench}.sv",
             f"assertions/sva_spi_{bench}.sv", f"tb/{top}.sv"], repo, log)
        output = run(["vvp", top], repo, log)
    counts = re.findall(r"^Tests (?:Run|Passed|Failed)\s*:\s*(\d+)\s*$", output, re.M)
    if (len(counts) != 3 or counts[0] != counts[1] or int(counts[0]) == 0 or counts[2] != "0"
            or "OVERALL RESULT : PASS" not in output or re.search(r"^(?:ERROR|FATAL):|\[FAIL\]", output, re.M)):
        raise BaselineError(f"SPI test summary or assertion failed; see {log}")
    return {"checks_run": int(counts[0]), "checks_passed": int(counts[1]), "checks_failed": int(counts[2])}


def uvm(repo, uvm_src, work, logs, jobs):
    build_log = logs / "antmicro-build.log"
    run([verilator(), "--version"], repo, build_log)
    obj = work / "antmicro-obj"
    # The upstream example allows library warnings. Preserve those diagnostics in the log.
    run([verilator(), "-Wno-fatal", "--assert", "--binary", "-j", jobs,
         "--top-module", "tbench_top", "--Mdir", obj, f"+incdir+{uvm_src}", "+define+UVM_NO_DPI",
         f"+incdir+{repo}", uvm_src / "uvm_pkg.sv", "sig_pkg.sv", "tb.sv"], repo, build_log, timeout=900)
    log = logs / "antmicro-run.log"
    output = run([obj / "Vtbench_top", "+UVM_TESTNAME=sig_model_test", "+verilator+seed+1"], repo, log)
    comparisons = len(re.findall(r"Sent length: .* Received length: .* are the same\.", output))
    if (comparisons != 10 or not re.search(r"Running test sig_model_test", output)
            or not all(re.search(rf"^UVM_{kind}\s*:\s*0\s*$", output, re.M) for kind in ("ERROR", "FATAL"))
            or re.search(r"^(?:UVM_(?:ERROR|FATAL)\s+[^\s:]|%Error|Assertion failed)", output, re.M)):
        raise BaselineError(f"UVM summary or expected scoreboard comparisons missing or failed; see {log}")
    return {"scoreboard_comparisons": comparisons, "uvm_errors": 0, "uvm_fatals": 0, "seed": 1}


def doctor():
    with tempfile.TemporaryDirectory() as directory:
        for name, command in {**TOOLS, "verilator": (verilator(), "--version")}.items():
            log = Path(directory) / f"{name}.log"
            path = shutil.which(command[0])
            if path is None:
                print(f"{name}: missing ({command[0]})")
                continue
            try:
                output = run(command, ROOT, log, timeout=10)
            except BaselineError:
                print(f"{name}: found at {path}, version probe failed\n{log.read_text()}")
            else:
                print(f"{name}: {output.splitlines()[1]} [{path}]")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=("doctor", "test-rtl", "test-uvm", "regress", "lint", "synth"))
    parser.add_argument("--jobs", type=int, default=4, help="parallel C++ build jobs for the UVM model")
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if os.name != "posix":
        parser.error("run this baseline from Linux or WSL2")
    if args.target == "doctor":
        doctor()
        return 0

    output = ROOT / "build" / "baseline"
    output.mkdir(parents=True, exist_ok=True)
    logs = Path(tempfile.mkdtemp(prefix="run-", dir=output))
    work = CACHE / "runs" / logs.name
    work.mkdir(parents=True)
    results = {}

    def record(name, action):
        try:
            details = action() or {}
        except BaselineError as exc:
            results[name] = {"status": "FAIL", "reason": str(exc)}
            print(f"FAIL {name}: {exc}", flush=True)
        else:
            results[name] = {"status": "PASS", **details}
            print(f"PASS {name} {details}", flush=True)

    def run_spi():
        repo = checkout("spi", work, logs)
        run(TOOLS["iverilog"], repo, logs / "iverilog-version.log")
        for bench in ("top", "master", "slave"):
            record(f"spi-{bench}", lambda: rtl(repo, bench, logs / f"spi-{bench}.log"))

    if args.target in ("test-rtl", "regress"):
        try:
            run_spi()
        except BaselineError as exc:
            results["spi-setup"] = {"status": "FAIL", "reason": str(exc)}
            print(f"FAIL spi-setup: {exc}", flush=True)
    if args.target in ("test-uvm", "regress"):
        record("antmicro-uvm", lambda: uvm(checkout("antmicro", work, logs),
               checkout("uvm", work, logs) / "src", work, logs, args.jobs))
    if args.target == "lint":
        def lint():
            repo = checkout("spi", work, logs)
            log = logs / "lint.log"
            run([verilator(), "--version"], repo, log)
            run([verilator(), "--lint-only", "--top-module", "spi_top", *sorted(repo.glob("rtl/*.sv"))], repo, log)
        record("spi-lint", lint)
    if args.target == "synth":
        def synth():
            repo = checkout("spi", work, logs)
            log = logs / "synth.log"
            run(TOOLS["yosys"], repo, log)
            run(["yosys", "-Q", "-T", "-p", "read_verilog -sv rtl/*.sv; hierarchy -check -top spi_top; "
                 "synth -top spi_top; check -assert; stat"], repo, log)
        record("spi-generic-synth", synth)

    (logs / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Logs and results: {logs}\nSimulation work directory: {work}")
    return int(any(result["status"] != "PASS" for result in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
