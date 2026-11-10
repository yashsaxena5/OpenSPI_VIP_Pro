# Working in OpenSPI-VIP Pro

- Use WSL2 Ubuntu or Linux for EDA commands. Run `make doctor` before changing the toolchain.
- Keep upstream inputs immutable and pinned. Preserve copyright, license, and NOTICE files for any source redistribution. Record paths, full commits, and local edits for imported code.
- Establish the affected protocol behavior in the specification before changing RTL. Use directed checks and lint before integrating UVM.
- Report the command, tool versions, source revisions, exit status, and observed outcome. Keep procedural RTL tests, UVM simulation, measured coverage, synthesis, and timing evidence distinct.
- Investigate diagnostics before adding waivers. Keep simulator-specific workarounds outside reusable VIP when possible.
- Preserve focused local commits. External publication requires explicit user direction and the user's employment and IP clearance.
- Use public references and original project material. Exclude all proprietary and employer-owned artifacts.
