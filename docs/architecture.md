# ADR 001 — SPI host and Wishbone register boundary

**Status** Proposed, 2026-11-10. The project maintainer owns acceptance of this register and pin contract.

## Context and decision

The first implementation needs one full-duplex word per command, a small synthesizable footprint, a Wishbone B4 Classic interface, and verification on open-source simulators. Use the audited `spi-sv-core` master as the behavioral and FSM foundation for a separately linted engine. Define the register block and wrapper in this project. Keep the upstream master, slave and loopback bench pinned for comparison. Qualify the Apache-2.0 SPI VIP candidate as a separate step, with an original Wishbone agent and independent predictor.

| Option | Assessment |
|---|---|
| Adapt the small upstream master | The original benches give a reference for four modes and full-duplex behavior. Runtime divider, CS indexing, reset, width-one legality and lint still require explicit work. |
| Build the engine from the register and pin spec | Gives direct control over the edge counter and boundaries. Requires independent qualification of all edge sequences from the first RTL commit. Use this path if adapting the FSM makes boundary behavior harder to verify. |
| Import OpenTitan SPI_HOST | Brings mature design patterns and richer SPI features, with TL-UL, generated registers and OpenTitan dependencies that are outside this controller's interface and scope. |

## Block boundary

```mermaid
flowchart LR
    M[Wishbone master] -->|CYC STB WE ADR SEL DAT| W[Classic request and CSR block]
    W -->|ACK ERR DAT| M
    W -->|Start and configuration| E[SPI host engine]
    E -->|Busy completion RX word| W
    E -->|SCLK MOSI CS_n| S[SPI target]
    S -->|MISO| E
```

All internal state uses `clk_i`. SCLK is an output data signal. `DATA_WIDTH` is an elaboration parameter in `1..32` with default 8. `NUM_CS` is in `1..16` with default 1. The first revision sends a fixed-width MSB-first word per CS assertion. Board-level MISO timing relative to SCLK must satisfy the chosen divider, external device delays and eventual I/O constraints.

## Proposed Wishbone profile

32-bit little-endian data, 8-bit granularity and one Classic single transfer at a time. Register offsets below are byte offsets and must be 4-byte aligned. Lane `SEL[i]` selects `DAT[8*i +: 8]`. Selected lanes merge on RW writes. Read data on unselected lanes is zero. Undefined or misaligned addresses, zero `SEL`, invalid access directions or fields, and disallowed busy writes terminate with `ERR`. `RTY`, pipelining and bursts are outside this revision.

Sample a request with `CYC && STB` at edge A. Present its latched response during A to B. At edge B, the master samples exactly one of `ACK` and `ERR` if it still holds `CYC && STB`. Commit any valid write at B. Withdrawal before B cancels the response and write. Capture the next request from edge C onward, including a new Classic request under an asserted `CYC`. Reset has priority and suppresses termination and side effects. Invalid writes leave state intact. Classify busy restrictions and snapshot read data at edge A, so completion coincident with A can be observed on a subsequent poll. [Wishbone B4 Classic specification](https://cdn.opencores.org/downloads/wbspec_b4.pdf)

| Byte offset | Register | Access | Reset | Fields and behavior |
|---|---|---|---|---|
| `0x00` | `CONFIG` | RW while idle | `0x0` | CPOL `[0]`, CPHA `[1]`, CS index `[7:4]`. Index must be below `NUM_CS`. |
| `0x04` | `DIV` | RW while idle | `0x2` | Half-period in `clk_i` cycles, `[15:0]`, range `1..65535`. |
| `0x08` | `TXDATA` | RW while idle | `0x0` | Low `DATA_WIDTH` bits hold the next word. |
| `0x0C` | `RXDATA` | RO | `0x0` | Last completed word, zero extended. Retained until a completion or reset. |
| `0x10` | `COMMAND` | WO | — | Selected bit `[0]` starts a word. Zero is a no-op. START while busy returns `ERR`. |
| `0x14` | `STATUS` | RO/W1C | `0x0` | `BUSY[0]` is read-only. Writing one to `DONE[1]` clears it. Hardware completion takes priority over a concurrent clear. Successful START clears old `DONE`. |

Reserved bits read zero. A one written to a reserved bit or to read-only `BUSY` in a selected lane returns `ERR`. Wishbone `ERR` signals rejection of the bus operation. SPI has no device acknowledgement, so `DONE` means that the host finished clocking the word.

## Proposed transfer timing

At a committed START, latch TX, divider, mode and CS index. Assert one active-low CS with SCLK already at programmed CPOL. Drive the first MOSI bit at selection for CPHA=0. The engine advances through `IDLE → SETUP → SHIFT → HOLD → IDLE`. Each SCLK edge occurs after `DIV` system cycles. The leading edge moves away from CPOL. The trailing edge returns to CPOL. Complete after exactly `2 × DATA_WIDTH` SCLK edges and another `DIV` cycles with CS asserted. At CS release, clear BUSY and atomically publish RX and sticky DONE.

| Mode | Idle SCLK | Leading edge | Trailing edge |
|---|---|---|---|
| 0 (`00`) | 0 | Rising, sample | Falling, change |
| 1 (`01`) | 0 | Rising, change | Falling, sample |
| 2 (`10`) | 1 | Falling, sample | Rising, change |
| 3 (`11`) | 1 | Falling, change | Rising, sample |

Example mode 0, two-bit word. Every `D` interval lasts `DIV` system clocks.

```text
Time         0        D        2D       3D       4D       5D
Event        select   leading  trailing leading  trailing release
CS_n         0        0        0        0        0        1
SCLK         0        1        0        1        0        0
MOSI         bit 1    bit 1    bit 0    bit 0    bit 0    0
MISO sample           ^                 ^
```

Synchronous active-high reset aborts any frame at the sampling edge, deasserts all chip selects, drives SCLK and MOSI low, clears RX/BUSY/DONE and restores the CSR defaults. The aborted word never publishes RX or DONE. Idle MOSI is zero. Changing CPOL while idle may move SCLK while all CS lines are inactive.

## Consequences and first implementation slice

A registered Wishbone response costs one wait interval and isolates the CSR decode from the bus termination path. One in-flight word gives deterministic CS and completion behavior. The firmware services each word, and multiword transfers will need a later interface revision. First qualify the standalone engine at widths 1 and 8, all four modes, and dividers 1 and 2 against an independent pin driver before connecting the Wishbone block. Extend to wider widths and multiple selects before adding FIFO or interrupt behavior.
