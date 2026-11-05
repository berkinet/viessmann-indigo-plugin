# Design context and open questions

## Confirmed by current handoff

The target is an Indigo plugin for Viessmann Vitotronic 200 KO1B/KO2B, using the existing Raspberry Pi running vcontrold on TCP 3002 and Optolink. Existing scripts populate the variables below. The exact installed controller variant, Pi address, versions, commands, and configuration have not been supplied.

## Variable inventory

Values are transcribed from the recovered screenshot, not live readings. Scope and native-state suitability are proposals. “Existing read” means a script-populated observation, not a verified controller command. No write capability is established for any row.

| Existing variable | Screenshot value | Proposed scope | Access / candidate Indigo representation |
| --- | --- | --- | --- |
| boilerTemp | 22.20 | System | Existing read; temperature state |
| burnerOutput | 127.5 | System | Existing read; numeric state, units/scaling unknown |
| burnerStatus | UNKNOWN | System | Existing read; status state, decoding unresolved |
| exhaustTemp | 20.0 | System | Existing read; temperature state |
| outsideTemp | 14.70 | System | Existing read; temperature state |
| pumpStatus1 | UNKNOWN | Heating / TBD | Existing read; status and scope unresolved |
| pumpStatus2 | 11.0 | Heating / TBD | Existing read; type, meaning, and scope unresolved |
| roomTemp | 21.00 | Heating | Existing read; candidate thermostat temperature |
| vctrlLastUpdate | 13-Nov-2025 10:42:08 | System | Script metadata; timestamp semantics unresolved |
| Vitocom100State | Off | System / TBD | Existing observation; source and relationship to vcontrold unresolved |
| warmWaterTemp | 25.00 | DHW | Existing read; candidate DHW temperature |

Temperature units must be confirmed. Names alone do not prove source, measurement semantics, or write support. Preserve names where practical to simplify existing Indigo automation migration; whether variables continue alongside device states remains open.

## Communications and devices

The shared manager owns communications and polling for the logical devices and distributes results. Connection lifecycle, request serialization, framing, timeouts, retries, polling cadence, freshness, and recovery behavior need design against actual scripts and vcontrold behavior. Coordinate coexistence or cutover with existing scripts before enabling polling.

The system device would expose shared temperatures, burner information, and communications health. Heating and DHW thermostat devices are candidates only. Confirm genuine measured temperatures, setpoints, modes, and supported writes before mapping native Indigo thermostat actions; no mode or setpoint commands are yet known. Pump ownership may differ from the provisional allocation.

## Unresolved observations

The earlier assistant flagged burnerOutput=127.5 as unusual if interpreted as a percentage, pumpStatus2=11.0 as unusual for an on/off state, and UNKNOWN values as possible decoding failures. These are hypotheses, not diagnoses. Verify XML conversion rules and raw responses before assigning meaning. Do not clamp values to conceal decoding errors.

The screenshot's vctrlLastUpdate is dated November 2025. This does not establish the age of the other values or prove the poller is stopped; determine how and when that variable is updated.

## Evidence required before implementation

1. Deployed vito.xml and relevant included configuration/conversion definitions; current scripts and their command/output examples, with credentials removed.
2. Actual controller model/variant and identification, installed vcontrold version, Pi endpoint, Indigo version, and supported plugin Python runtime.
3. Command matrix recording exact command, source definition, scope, type, unit, conversion, supported values, read/write status, and observed read evidence.
4. Heating circuit and pump mapping; origin of roomTemp and Vitocom100State; DHW sensors and supported controls.
5. Native Indigo control mappings, supported modes/setpoints and limits, variable compatibility requirements, polling interval, freshness policy, and coexistence/cutover strategy.

Begin with verified reads and fixture-based parsing/communications checks when implementation starts. Any future write needs verified command semantics, limits, and a deliberate validation plan. Nothing in this migration authorizes exploratory writes.

## Current equipment availability — 5 November 2026

The owner confirmed the heater unit is currently out of service. Read timeouts during the daemon upgrade are consistent with that condition and do not establish a transport defect. Continue offline design and implementation using clearly labelled fixtures; defer real controller validation until the heater is available. Do not enable existing polling or attempt writes as part of offline development.

## Owner-confirmed architecture — 5 November 2026

This section supersedes earlier provisional assumptions about multiple heating circuits or separate water-heating equipment.

One physical boiler serves central heating and domestic hot water; DHW is heated through a heat exchanger within that boiler. Three logical Indigo device types are agreed as the baseline:

- Viessmann system: parent device owning connection configuration, boiler-wide mode, shared hardware measurements, diagnostics and freshness.
- Viessmann heater: central-heating function and its verified settings/states, referencing the system device.
- Viessmann water heater: DHW function and its verified settings/states, referencing the same system device.

One shared communications/polling manager serializes requests and distributes readings. Do not assume additional circuits. The controller knows measured room temperature, but no verified vcontrold retrieval command is currently available. Existing roomTemp reads getRoomTempSP and must not be represented as measured room temperature.

The owner initially reported off; heat only; heat and hot water. This was corrected by the model-specific manual; see docs/manual-modes.md. The verified normal programs are standby, only DHW, and heating and DHW. These are boiler-wide settings owned by the system device. Their configured permissions are:

| System mode | Central heating enabled | DHW enabled |
| --- | --- | --- |
| Standby (frost protection active) | No | No |
| Only DHW | No | Yes |
| Heating and DHW | Yes | Yes |

Enabled means permitted by the reported mode, not actively running. Burner activity alone cannot establish which function is active. Only DHW is a documented program; do not invent a separate heat-only program. Low-level command, encoded values, mode readback, and any protection behavior in off remain unverified. No writes are authorized merely by documenting these modes.

Recommended initial control model: one mode selector on the system device; functional devices reflect that shared mode and expose only verified function-specific settings. Independent functional on/off actions and native thermostat mappings remain design questions because they could change shared mode. Do not silently invent transitions or discard these coupling constraints.

## Subsequent Vitodata evidence

See vitodata-observations.md. The website displays configured mode 1 as Only DHW, conflicting with the earlier owner-reported heat-only mode. The preceding operating-mode table is provisional pending clarification and must not drive controls. The screenshot also explicitly distinguishes measured room temperature from standard/reduced/party setpoints and current operating state from configured mode.

## Manual verification supersedes mode uncertainty

See manual-modes.md: Viessmann 5592667 GB (3/2018), page 16, confirms Standby, Only DHW, and Heating and DHW. Page 29 describes a separate setpoint procedure for heating without normal DHW heating, not a fourth program. Earlier heat-only statements and requests for owner confirmation are superseded. Numeric command encoding remains unverified.

## iOS program selector expands the candidate list

See manual-modes.md: the subsequent iOS screenshot displays five choices, adding Continuous reduced and Continuous standard to the three manual-described normal programs. The full remote-control program set is not yet verified. Preserve these candidate choices without assigning protocol codes or DHW behavior; design program capabilities explicitly rather than hard-coding three total possibilities.

## Agreed operating-program abstraction

The owner agreed to expose named operating programs at the Indigo level without requiring a one-to-one mapping to controller mode values. A program may ultimately map to one command or a verified combination of settings; this is an implementation concern of the shared communications layer.

Keep selected/configured program separate from observed burner activity, heating pump activity, DHW heating activity, and communications availability. Do not infer actual activity from program selection. Preserve the existing three-device architecture.

The five app-displayed choices remain candidate programs, not confirmed writable capabilities. Before enabling a write, verify the mapping and readback. If multiple commands are needed, serialize the operation, detect partial failure, read back the resulting state, and do not report success merely because commands were sent. Multi-command atomicity or rollback must not be assumed. Unknown or inconsistent readback must remain explicit rather than being guessed into a named program.

## Limited accessible capabilities

The owner emphasized that only a small subset of the system's actual functions and controls is accessible. The three logical device types describe responsibilities, not a promise of full Vitodata/iOS parity.

Expose only supported capabilities: distinguish documented controller features, declared XML commands, observed successful reads, and verified writes. A website/app control or an XML declaration alone does not qualify as usable plugin control. Initially, the four legacy script read mappings are known, but live responses cannot be validated while the heater is out of service; no writes are verified.

Keep unsupported controls absent or explicitly unavailable rather than simulating them or presenting misleading success. Preserve room setpoint versus measured temperature, and selected program versus actual activity. The five app programs are reference candidates, not an initial implementation requirement. Prioritize the small accessible subset; expand only when evidence supports it. Native Indigo device/control choices must fit that subset and must not imply unsupported functionality.

## Initial implementation decisions

The owner confirms the legacy read-only script ran every three minutes. Polling is a system-device property in seconds, default 180. Use a persistent TCP connection and explicitly release Optolink using close after each cycle, retaining TCP for reuse and possible future protocol extensions. Current upstream source is request/response; no change subscriptions were found. Future push notifications require explicit framing and routing, not numeric extraction from arbitrary incoming text.

See runtime.md for initial read-only implementation scope, per-reading validity, lifecycle, timeout behavior and offline verification. Functional devices remain custom read-only devices until native thermostat semantics and writable controls can be supported accurately.

## Selected room-target presentation

The owner proposes that the native thermostat's single setpoint represent whichever room target is selected through configuration or actions. Normal and standard are confirmed synonyms; the targets are standard/normal, reduced and party. Switching the selected target must change the displayed value, label/context, and eventual write destination together. Keep the chosen editing target distinct from measured temperature and boiler operating program. Whether target selection should also activate a controller mode remains to be agreed; no such side effect is implemented. Native thermostat conversion and write support have not yet been implemented.

An isolated vsim plus real-vcontrold environment is now installed; see simulator.md. Synthetic successful responses validate software plumbing only.
