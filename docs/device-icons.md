# Device icons and burner diagnostics — 0.2.16

Both native thermostat children explicitly select Indigo's TemperatureSensor icon. This changes only their preferred state images, not device class, temperature display or thermostat controls. Existing Indigo error/pending display behavior remains in force.

The system device uses HvacHeating for provisional stage-1 activity 01, HvacOff for 00, neutral SensorOff for unknown activity/lost communication, and SensorTripped when an active fault is displayed. Faults take precedence. Icon overrides are cached and do not modify capability properties. Selection uses the states being published rather than assuming the local Indigo snapshot has refreshed.

Activity is read with getProbeBurner1 at 0842/1, accepting only raw 00/01. This exact-model digital-output candidate is preferred over getBrennerStatus at 551E, which returned UNKNOWN. It is not proven flame detection. Reads use the error/status interval, default 60 seconds. Failed/05 responses invalidate activity.

The system also exposes burnerOutput, burnerOutputValid, burnerOutputUpdated, burnerOutputRaw and burnerOutputError. getBurnerOutput uses 55E3/1/PR; PR is short with V/2 scaling. This unusual one-byte/short definition is retained unchanged and treated as provisional. Accept only numeric percentages from 0 to 100, optionally suffixed with %. Zero is valid. Preserve prior numeric readings on failures with validity false. Percentage output does not drive the icon yet; the owner agreed to observe it first.

getProbeProductionStatus (A395) was also suggested as a burner-on signal. Its first byte returned 00 earlier, but those samples were not a clearly time-aligned confirmed burner-on comparison. Its layout remains unknown; it is neither ruled out nor used for the icon.

Validation: 44 offline tests passed, covering fixed icons, active/idle/unknown/fault precedence, immutable device snapshots, percentage bounds/zero and failed-read retention. Native rendering awaits owner installation/observation. No local upgrade or heater write was performed.
