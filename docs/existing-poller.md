# Existing Indigo polling script

Inspected on 5 November 2026, without execution or modification:
`/Library/Application Support/Perceptive Automation/Scripts/vcontrol.py`.
The file was 4497 bytes, with filesystem modification date 10 August 2025. Its invocation schedule and actual runtime success have not been verified.

## Confirmed active mappings

| Indigo variable | vcontrold read command | Interpretation |
| --- | --- | --- |
| boilerTemp | getBoilerTemp | Boiler temperature |
| outsideTemp | getOutsideTemp | Outside temperature |
| roomTemp | getRoomTempSP | Normal room setpoint candidate, not a verified measured temperature |
| warmWaterTemp | getWaterTemp | Hot water temperature |

The script connects to TCP port 3002 and waits for `vctrld>`. It sends newline-terminated commands and ends with `quit`. It updates vctrlLastUpdate with a local datetime string after completing collection, then updates the result variables. This timestamp is not proof that every reading was valid or that every variable in the screenshot was refreshed.

Commented mappings: burnerOutput/getBurnerOutput, exhaustTemp/getExhaustTemp, pumpStatus1/getPumpStatus, pumpStatus2/getPumpStatusSp, and brennerStatus/getBrennerStatus. The last name differs from the screenshot variable burnerStatus. Do not silently carry that typo into the plugin.

Vitocom100State has no mapping or update in this script. Other scripts/actions may maintain it. Disabled values in the screenshot cannot be treated as current or diagnosed solely from this script.

## Implementation implications

- roomTemp is confirmed to call getRoomTempSP; the deployed XML pairs its address with the normal M1 room setpoint write. Keep measured temperature and setpoint separate in the device design.
- The script imports telnetlib and expects Indigo's injected `indigo` object; its explicit import is commented out. Do not execute it as a standalone diagnostic. Choose plugin transport against the actual supported Indigo Python runtime.
- Initial connection and prompt wait have no explicit timeout. Subsequent reads stop at a newline with a five-second timeout, not at a complete prompt-delimited response. The expect match status is not checked. The plugin needs bounded connection/read deadlines and complete response framing.
- A regex extracts the first number from arbitrary response text. That can misclassify diagnostics as measurements. Use command-specific validated parsing and explicit error handling.
- The retry loop rejects both 128.5 and 0.0. Zero is a potentially valid temperature; repeated zero/sentinel results do not increment the exception counter and can loop indefinitely. Preserve legitimate zero and negative readings, and bound retries independently of returned values.
- Exceptions increment a per-command counter; the bare catch can obscure the cause. Some intermediate counts retry without delay. Reconnect and retry policies must be explicit and bounded.
- A parsing failure sends quit but can still place text into results, then continue using the session. Do not publish parsing failures as valid device states.
- Variables are updated after collection, with the timestamp first. Define last-attempt versus last-success and per-reading freshness; avoid implying an atomic successful snapshot when updates or parsing fail.

No script fixes or polling cutover have been performed. Before plugin polling starts, establish the existing Indigo action/schedule and prevent overlapping pollers. Live command responses, controller identity, units/limits, and native control suitability still need validation. All boiler writes remain disabled.

Source SHA-256: `9bf423be55fdf70b455160ac9e7ad565470094c25140c13008fb2c958e7a8663`.

## Indigo schedule

The owner identified `indigo.schedules[1256701943]`, named `Viessmann-Query`, as the caller. A read-only Indigo connector lookup on 5 November 2026 confirmed that identity and reported `configured=true`, `enabled=false`, and `nextExecution=null`, in folder `frequent`.

The schedule is currently disabled. This may explain why the screenshot's update timestamp is old, but does not establish when it was disabled, when the script last ran, or whether another caller exists. The returned properties did not expose the action body or a human-readable recurrence interval, so the invocation details and cadence remain unverified. No schedule was executed, enabled, or modified.
