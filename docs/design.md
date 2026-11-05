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
