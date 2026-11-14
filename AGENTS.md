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

## Optical activity probe and repair hold

The owner states the heater must stay off pending repair (reported 6 November 2026). Do not power it on or perform live controller tests until the owner explicitly resumes them. Offline source research, fixtures and simulator development remain authorized. See docs/optical-activity.md for the fixed receive-only raw script, KW/KW2 gating and interpretation limits. Optical activity, valid data communication and active fault status are separate observations. Boiler-temperature mapping was deferred during the optical probe release and implemented in 0.2.11 after the owner reported the live blank display; see docs/thermostat-trial.md. The owner explicitly resumed production communications on 13 November and subsequently reported the heater running.

## Nameplate-confirmed controller identity

On 8 November 2026 the owner supplied a photograph identifying the installed controller as **Viessmann Vitotronic 200, type KO2B**. Use KO2B for model-specific research; earlier KO1B/KO2B wording describes the broader family. This is the controller identification, not evidence of the boiler/burner model, firmware revision or supported protocol commands. Source image: `/Users/rdp/Desktop/Screenshots/Screenshot 2026-11-08 at 14.01.46.png`.

## Owner-authorized live-write opt-in (0.2.12)

On 13 November the owner requested live standard-room and DHW writes selectable in plugin configuration, superseding the earlier blanket simulator-only rule for those two targets only. Default remains off. Require exact KO2B identity, a fresh complete error-free snapshot, bounded whole-degree target, acknowledgement and matching readback; no retries of uncertain writes. Reduced/party remain simulator-only. The first unchanged live setter validation failed acknowledgement; physical write effectiveness is still unverified. See docs/thermostat-trial.md. Never enable the preference on the owner's behalf or interpret the feature as permission for unrelated writes.

## Verified room measurement — 13 November 2026

The owner confirmed measured room temperature tracking 20.6 -> 20.7 C alongside live getProbeRoomTemp (0896/2/UT). Earlier statements that measured room temperature is unavailable are superseded for this installed KO2B. Existing plugin display still uses provisional boiler temperature until deliberately changed; see docs/live-probes-2026-11-13.md. Keep the pending-set display changes unpublished until owner authorization.

## Unpublished lifecycle revision (owner-directed, 13 November)

The owner requested persistent TCP **and** optical ownership, establishing health via getSystemTime and keeping the optical link open between commands. This supersedes the earlier close-after-every-cycle and complete-snapshot-before-every-write instructions for the local 0.2.15 implementation. Clock health defaults to 30 seconds, independent error-history/relay sampling to 60 seconds, full readings to the existing 180 seconds; all are configurable on the system device. Writes remain opt-in, exact-identity checked, bounded, target-read/ACK/readback confirmed and never automatically retried. Measured room temperature is now the heater's native default. Do not infer an active fault from getError0 alone or invent an A152 bit mapping. Preserve established faults until explicit verified clear evidence; production of that evidence remains unimplemented. Maintain the publication hold: no push, release or installed-plugin update until instructed. Local simulator clock support is also unpublished.

## Relay display trial authorized; publication requires owner OK

The owner explicitly authorized coding the A152 first-byte mask 01 interpretation for display after D1/clear observations. This supersedes the prior prohibition on adopting that bit in the local draft: implement it as provisional and exact-KO2B-scoped, reject bad/05 05 samples, retain last state on unknown, and use history only for the code while the relay indicates an active fault. It must not affect write permissions or physical controls. Owner then required a consolidated change summary and explicit OK before pushing to GitHub. No push, release or installation until that OK.

## Publication approved — 13 November 2026

After reviewing the local changes and measured-room display mapping, the owner explicitly approved push/publication of 0.2.15 and returning to the normal workflow. This lifts the earlier publication hold. Standing commit/push/publication authorization resumes; do not ask repeatedly. Indigo installation remains owner-managed through GitHub downloads. The temporary restart monitor was stopped and its capture archived to avoid competing with the new persistent optical owner.


## Holiday support authorized — 14 November 2026

The owner authorized live holiday get/set discovery, supplied future departure/return test dates (final 20 November / 13 December 2026), and requested plugin support and publication. This extends the prior permitted live-write targets to future holiday departure/return dates only, through the existing live-write opt-in. Exact KO2B identity, fresh reads, per-register acknowledgement and readback remain required. Do not retry uncertain writes or imply an atomic pair update. The tested normal TI setter path requires the vcontrold daemon to run UTC; heater dates remain local calendar dates. Active-holiday replacement and cancellation are not implemented.

The owner requested explicit Unset, Set (not active), and Active states and periodic rereads to capture changes through the controller/app; invalid or conflicting reads must remain Unknown with validity false. Keep the distinction between exact-catalog active-bit metadata and an observed active holiday: only unset and future/inactive schedules have been live-tested. See docs/holiday-command-tests-2026-11-14.md.

Display time must be local to the heater location, not the viewer. The system heaterTimeZone property defaults to Europe/Paris; lastHealthCheckLocal uses that zone with daylight-saving rules. Preserve the existing UTC timestamps for logs and comparisons. Owner installs releases from GitHub; do not install locally on their behalf.
