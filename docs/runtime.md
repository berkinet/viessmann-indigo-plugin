# Initial read-only plugin (0.1.0 development build)

## Setup and scope

The source bundle is Viessmann.indigoPlugin. It targets Indigo's Python 3 Server API 3.9, following the installed Indigo plugin bundle conventions. No third-party Python packages are required. It has not yet been installed or loaded in a live Indigo plugin process.

When ready for an Indigo smoke test, install the bundle through Indigo, then create one Viessmann system device. Enter the Pi hostname/IP and TCP port (default 3002). Polling is disabled by default; leave it disabled while the heater is out of service. Create Viessmann heater and Viessmann water heater devices and select the same system as their parent. They are custom read-only devices, not native thermostats yet.

The system property Polling interval (seconds) defaults to 180, matching the owner's three-minute legacy schedule. Allowed range: 30–86400 seconds. The interval starts when the previous cycle finishes, so cycles never overlap or produce catch-up bursts. Response timeout defaults to 12 seconds per command (range 1–60); connection establishment is limited to five seconds. A changed configuration resets the connection and makes the next cycle due immediately. Reconnection is attempted on the next scheduled cycle after a transport failure, not in an unbounded retry loop.

This first version supports one system device and one physical boiler. Both functional child types share its single manager. Duplicate system devices are rejected by validation and fail closed if imported configuration bypasses validation. Child devices cannot create their own TCP sessions.

## Supported read mappings

| Device | State | Existing vcontrold command |
| --- | --- | --- |
| System | boilerTemp | getBoilerTemp |
| System | outsideTemp | getOutsideTemp |
| Heater | roomSetpoint | getRoomTempSP |
| Water heater | warmWaterTemp | getWaterTemp |

These mappings are established by the existing script and deployed XML, but successful live readings still need validation when the heater returns to service. Temperature parsers accept a single numeric value, optionally followed by C, and preserve zero/negative values. Fixtures are synthetic; actual successful response spelling must be checked before enabling normal use.

roomSetpoint is deliberately not called roomTemp: the existing variable reads a setpoint, not a measured room temperature. Existing Indigo variables are not written, and the legacy script/schedule is not changed. The owner identifies its previous cadence as three minutes. No burner/pump states, operating-program writes, setpoint writes, or synthetic thermostat actions are implemented.

## Persistent TCP and optical-link ownership

One connection remains open between cycles. Each cycle reads the four mappings once, then sends vcontrold's close command and consumes the returned prompt. This releases the serial/Optolink transaction without closing TCP. Plugin shutdown, disabled polling, changed settings, or stopped parent closes TCP. A framing or transport failure discards the connection rather than sending further commands into an unsynchronized stream. A failed link-release acknowledgement also discards it.

Source evidence: https://github.com/openv/vcontrold/blob/v0.98.36/src/vcontrold.c (interactive loop, close branch, and first serial-command acquisition). Current vcontrold is request/response; no subscription or change-push protocol was found there. A persistent socket provides a foundation for a future extension, but unsolicited notifications are not currently supported by this parser and would require explicit framing and dispatch.

## Validity and errors

Numeric values retain their last successful reading after failure; each has a separate Valid flag and Updated UTC timestamp. Do not treat an initial Indigo numeric default as a real reading. dataValid identifies the latest completed cycle's validity for that device. System dataValid covers all four readings and successful optical-link release. Child validity concerns its own reading; lastError can additionally report a shared link-release failure. tcpAvailable means that TCP was usable at the start of the last attempt, not a continuous connectivity monitor and not proof of heater availability.

lastAttempt is recorded on completion of an attempt, and lastSuccess on completion of a valid device snapshot. Timestamps are UTC ISO strings. While polling is disabled, or the parent/plugin is unavailable, validity is cleared. Between cycles, last-success timestamps show reading age; there is no independent push freshness watchdog in this version.

Read errors are device states, not substituted values. Parsing matches the full response, so UNKNOWN or a diagnostic containing digits cannot become a temperature. Command dispatch is restricted to the four reads and close; there is no free-form command entry.

## Verification

Run from the project directory:

```zsh
python3 -m unittest discover -s tests -v
```

Build a clean installer archive with `python3 tools/package.py` (output under dist/).

Tests use a local synthetic TCP server and a minimal Indigo API double. They cover persistent connection reuse, successful/failed release, fragmented responses, zero/negative readings, diagnostics, timeout recovery, read-only dispatch, cancellation, polling cadence/configuration, child distribution, and invalidation. They do not establish real-controller compatibility or live Indigo loading.

No code was installed into the operational Indigo installation, no schedule was enabled, and no further Pi/controller reads were required for this implementation.
