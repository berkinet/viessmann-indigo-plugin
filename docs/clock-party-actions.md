# Clock and party actions — 0.2.24

All three actions run through the existing serialized communications manager.
They require enabled polling, explicit live-write opt-in and exact KO2B identity.
Each requires current-value reads, acknowledgement and matching readback; uncertain
writes are never automatically retried. Endpoint or preference changes invalidate queued actions.

## Actions

- System: **Set controller clock from Mac server time**. Samples the Mac clock at
  worker execution, converts that instant to the system device's heaterTimeZone
  (default Europe/Paris), and writes those local calendar fields. This is an
  explicit action, not an automatic clock adjustment. clockActionStatus records
  success or failure; controllerTime receives confirmed readback.
- Heater: **Set party room temperature**, whole degrees 4–37 C. It changes the
  party target without enabling party mode or changing the selected thermostat target.
- Heater: **Set party mode On / Off**. Explicit On or Off, never a toggle based on
  possibly old UI state. It does not set the temperature.

partyTemperature and partyMode are last successful action readbacks, not continuously
polled telemetry. actionStatus records pending/confirmed/error. External changes
are not reflected in these two new states until another corresponding action.
Existing selected-party thermostat target polling remains unchanged.

## Command evidence and transport

The exact KO2B DPDefinitions catalogue lists Uhrzeit at 088E/8, party room target
at 2308/1 (4–37, step 1), and NRx_PartybetriebA1M1_D at 2330/1 (0=Off, 1=On).
Existing get/setSystemTime use TI; getTempPartyM1/setTempPartyM1 use ST.
New getPartyModeA1/setPartyModeA1 use RT. The legacy party commands at 2303 were
left untouched: their address does not match this KO2B catalogue entry.
See config/party-commands.xml for the installed additions. RT must decode 0 and 1.

The deployed daemon runs UTC. Its TI parser applies the supplied offset before
encoding controller calendar fields. Accordingly the clock action sends heater-local
fields with the transport suffix +0000, as used by our verified holiday path.
This suffix describes the daemon transport, not the heater's geographical zone.
The action refuses another daemon offset. Readback must be within one second
behind to elapsed request time plus three seconds ahead of the requested instant.
The real clock setter was not invoked during this release's validation.

Live validation on 15 November wrote back the existing party target 15 C and
existing party mode 1 (On); both returned OK and identical readback. No mode or
target change was requested. The first attempted XML layout placed all fields
under a device override and crashed this vcontrold parser at startup. Production
was restored from backup. The corrected ordinary command layout was startup-tested
against /dev/null before unchanged-value live tests, then production was restored.

## Recovery regression

A failed full poll previously removed SupportsHeatSetpoint and a later success
restored it. This can race Indigo's asynchronous native-state schema and produce
setpointHeat-not-defined errors. Established supported capability now survives a
failed reading while live-write opt-in remains enabled. State validity and write
health checks remain independent; failed reads do not authorize writes. Disabling
writes or selecting an unsupported target still removes the capability. Native
updates retain the existing state-presence guard.

Offline coverage includes clock zone conversion/offset rejection, invalid party
values, opt-in, missing readback/no retry, queued endpoint changes and connection
loss/recovery without native schema removal. Installation remains owner-managed.

## Version 0.2.25 — live toggle and party setpoint following

Toggle party mode reads getPartyModeA1 at execution and writes its opposite, with
ACK/readback and no retry. Repeated clicks while the same device has a toggle
pending coalesce. Explicit On and Off actions remain available.

Party mode and the effective room target are read at each full poll and each
fault/status sampling interval (normally 60 seconds). This captures external
changes. partyModeValid, partyModeUpdated and partyModeError describe validity;
partyModeText is On, Off or Unknown. An old boolean is retained on failure but
never presented as a valid current mode. No flame/burner inference is involved.

When confirmed On, roomSetpoint and native setpointHeat follow getTempPartyM1.
Otherwise they return to the configured roomTarget; no configuration is silently
changed. This is not yet automatic selection between standard/reduced according
to the heating schedule. selectedTarget identifies the displayed editing target;
roomTargetIndicator supplies the small Party label on the control page.
The label and temperature update together after the target has been read.

Native thermostat writes recheck party mode before selecting the register; if it
changed since the displayed target was chosen, the write is rejected for explicit
retry after refresh. After switching mode, edits wait for target readback. The
dedicated Set party room temperature action still edits the party target without
activating it. Unknown target/mode does not become Off or a valid target.

Owner confirmed live clock synchronization and party-mode actions successful after
0.2.24 installation. The new transitions/toggle routing were fixture-tested; no
physical mode changes were performed while developing 0.2.25.
