# Development instructions

## Project scope and evidence

Build an Indigo plugin for Vitotronic 200 KO1B/KO2B using the existing Raspberry Pi, vcontrold TCP port 3002, and Optolink. Read README.md, docs/design.md, and docs/migration.md before implementation.

Use a single shared TCP communications/polling manager. Consider three logical devices (system, central heating thermostat, domestic hot water thermostat); this device split is provisional. Do not create independent competing polling connections for logical devices.

Verify actual command names, addresses, types, units, scaling, enumeration meanings, scope, and read/write support using the deployed vito.xml and scripts. Record evidence and uncertainties. Do not infer supported commands from parameter names or another controller model. No unverified writes to the boiler. Initial discovery is read-only; unsupported controls must remain unavailable.

Preserve the 11 existing Indigo variable names where practical. Do not silently convert UNKNOWN, decoding errors, or stale data to valid readings. Do not assume the screenshot is current telemetry. Native Indigo control mappings and version compatibility require verification before implementation.

## Working preferences

Use zsh unless another shell is specifically required. Exercise independent judgment, explain evidence and tradeoffs, and preserve unresolved questions rather than inventing details.

The owner permits commits, pushes, and publication within requested work unless more specific instructions override that permission. For this project, do not create a GitHub repository until the owner explicitly confirms its name and visibility. Do not delete the source ChatGPT project or history as part of migration.

## Tests

At stage transitions (alpha, beta, release), after substantial design changes or refactoring, and periodically during sustained development, review relevant tests proportionally. Before starting a review, notify the owner of its trigger and proposed scope; this is notice, not an approval request.

Keep tests focused on requirements, meaningful failure modes, and plausible regressions. Update or remove obsolete tests, consolidate redundant coverage, and retain valuable regression protection. Avoid tests that mirror implementation. Account for maintenance and runtime costs; inspect selectively and report significant coverage changes and reasons. Do not treat test count as evidence of quality. The project now includes a read-only implementation; run the meaningful offline simulator and Indigo-adapter tests when communications or lifecycle behavior changes.

## Confirmed system model

Follow the owner-confirmed architecture section in docs/design.md over earlier provisional device/circuit assumptions: one boiler with internal DHW heat exchanger; Viessmann system, Viessmann heater, and Viessmann water heater logical devices; shared communications manager. Manual-verified normal operating programs are Standby (frost protection active), Only DHW, and Heating and DHW. See docs/manual-modes.md; the earlier heat-only description is superseded. Mode encodings and native Indigo action mappings remain unverified. Measured room temperature is known to the controller but not currently retrievable through a verified vcontrold command; roomTemp in the legacy script is a setpoint.

Mode clarification pending: the later Vitodata screenshot shows mode 1 as Only DHW, conflicting with the earlier heat-only description. See docs/vitodata-observations.md; do not implement the earlier mode truth table until resolved.

The model-specific manual now resolves the semantic mode discrepancy; numeric protocol encodings remain unverified. Do not implement a heat-only program or silently lower the DHW target to simulate one.

The later iOS screenshot shows five program choices, including Continuous reduced and Continuous standard. The manual documents three normal programs, not a proven exhaustive remote-control list. See docs/manual-modes.md; keep support capability-driven and do not invent continuous-mode semantics or numeric encodings.

The owner emphasizes limited accessible functions/controls. Do not aim for Vitodata/iOS parity or expose controls solely because the app/manual/XML lists them. Scope implementation to verified accessible capabilities; the five app programs are reference candidates, not promised support.

Implementation baseline: persistent TCP owned by one manager; close releases Optolink between cycles without closing TCP. Poll interval defaults to 180 seconds on the system device. Polling starts disabled; do not enable live polling while the heater is out of service. See docs/runtime.md.

## Distribution and thermostat trial

The owner downloads installers from GitHub and performs installation. Publish versioned release assets; do not initiate local Indigo upgrades unless explicitly asked. Current prototype uses native thermostat children with selectable standard/normal, reduced, and party room targets. See docs/thermostat-trial.md. Physical writes remain blocked. Only the positively marked simulator may accept bounded setpoint commands with acknowledgement and readback; the marker must never be added to physical-controller configuration. Preserve the system device and its settings when migrating child classes.
