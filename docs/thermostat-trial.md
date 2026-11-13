# Native thermostat trial — 0.2.1

Download the installer asset from the project's GitHub release page and install through Indigo. The owner prefers GitHub downloads and performs installations; do not initiate local upgrades without an explicit request. The attempted local 0.2.0 upgrade from the synced source folder failed after Indigo trashed the old bundle; retry from a temporary local copy installed 0.2.0. No further local update was performed after the owner's correction. The next download is the fixed 0.2.1 prerelease.

## Devices and migration

The system device stays custom and retains the endpoint/poll interval. The heater and water heater definitions are now native thermostat types, with cooling, fan, generic HVAC mode and activity indicators disabled. Additional custom diagnostics remain available.

Keep the existing system device. After upgrading, inspect each child for Thermostat Controls. If Indigo retains the old custom device class, recreate only the two children, using the same parent system and desired names. Do not delete the parent or alter unrelated devices. In this initial one-system design only one active heater child is supported, so disable/remove the old heater before activating a replacement. Existing automations that referenced a recreated child's ID would need updating. No child was deleted or recreated by the agent.

Heater configuration has Room target to display/edit: Standard / normal, Reduced, or Party. The plugin action Select room target to display/edit changes the same property. This selects which target the native heat-setpoint arrows edit. It does not activate party mode or change the boiler operating program. The selectedTarget custom state and SIMULATOR status label identify the current choice.

The heater's temperatureInput1 is a separate simulated room measurement (about 20.7 C), never its setpoint. On a non-simulator endpoint the unverified room input is omitted. The water heater's temperatureInput1 is the DHW measurement (46 C fixture) and its heat setpoint is the DHW target (50 C fixture). Heat-setpoint label text is supplied by Indigo.

## Simulator-only controls

The simulator XML now identifies its 209F device as SIMULATOR_209F. The transport checks the exact device metadata response on the active socket immediately before any setter. Non-simulator identity rejects the write before sending a setter. This operational marker distinguishes the configured test endpoint; it is not network authentication and must not be copied to physical-controller XML.

Only four setpoint commands are supported, through one serialized manager: standard, reduced, party, DHW. Values must be whole degrees in the fixture ranges (room 3–37 C, DHW 10–60 C). These are trial limits, not verified physical-controller limits. Write success requires OK plus matching readback, followed by optical-link release. Ambiguous results are not retried. UI state changes only after confirmed readback; a full refresh follows. Requests queued before an endpoint or selected-target change are rejected.

The isolated vsim copy was extended with stateful single-byte KW2 writes at 2306, 2307, 2308 and 6300. These update the corresponding read fixtures, and reset when vsim restarts. Four matching setters were added only to the TEST XML. Physical-heater XML and its write definitions were untouched. The test vcontrold now uses its normal forked-client mode under a Type=forking systemd unit, allowing Indigo and verification clients simultaneously while serializing simulated-link access. Endpoint remains 192.168.5.37:3002; vsim backend remains loopback 6578.

Preparation helper enable_thermostat_trial_on_pi.py documents the one-time extension, refusing to overwrite its before-thermostat backups. It was already applied to the Pi. The normal fixture helper still creates the original read-only environment; the trial helper is an additional step. No changes to boiler program, pumps, or measured temperatures are simulated by target selection.

## Verification and limits

Offline tests cover protocol framing/reconnects, non-simulator rejection, bounds, native temperature versus target, target switching, queued relative actions, rejection after config changes, and immediate refresh after capability restarts. The 0.2.1 lifecycle fix avoids resetting native capabilities every time a device restarts and makes startup/reconfiguration immediately due for polling.

Real vcontrold plus vsim successfully polled all six prototype values and accepted/read back changes to all four targets. Each test restored the original synthetic target afterward. 0.2.1 has been packaged and checked offline but is awaiting the owner's GitHub installation and native UI trial. Real heater registers, native class migration and writes are not established by simulator success.

## Confirmed native UI and 0.2.2 status refresh

The owner installed 0.2.1 from GitHub, recreated the two child devices, and confirmed that both thermostat roles and readback-confirmed setpoint changes work against the simulator. The system device was retained. The screenshot shows measured room temperature separately from the selected standard target and actionStatus=Simulator readback confirmed.

Version 0.2.2 enables Indigo's Send Status Request capability on all three device types, including migration of existing saved properties. The universal action callback queues a refresh in the shared worker, never a second connection or a write. Either child's request refreshes the same shared snapshot as a system request. Repeated queued requests coalesce. A manual request is permitted with automatic polling disabled but does not enable periodic polling; its validity remains until a subsequent attempt or configuration/lifecycle transition, with timestamps showing age. Changed/stopped parent configurations cannot retain a pending one-shot request.

Targeted tests cover callback routing, coalescing, disabled one-shot operation and enabled-to-disabled invalidation. The real vcontrold/vsim endpoint also completed one shot with automatic polling disabled, without resetting the owner's synthetic setpoints. The 0.2.2 build awaits the owner's GitHub installation; no local installation was performed.


## 0.2.3: accessible system refresh

The owner confirmed that the custom system device does not show a Send Status Request button, even when recreated. The 0.2.2 capability flag did not provide that UI; the earlier implication that it would was incorrect. Thermostat children retain their native buttons.

Version 0.2.3 adds Plugins > Viessmann > Request system status, plus a device action named Request status for all three device types. Both use the existing serialized shared refresh path, including one-shot reads while periodic polling is disabled. The device action can also be assigned to a Control Page button. No device recreation is needed. Installation remains owner-managed through GitHub.


## 0.2.4: connection versus read failures

The device status and Indigo error banner now say Connect failed when TCP connection establishment fails, with host:port and the underlying error in lastError. Read failed means TCP connected but the greeting, protocol response, reading, or link release failed. tcpAvailable records TCP establishment, not successful heater communication; a greeting timeout therefore counts as Read failed. Existing measurements and validity handling remain unchanged.


## 0.2.5: Pending for incomplete snapshots

When TCP connects and the current shared poll returns some valid readings, devices missing their required data show Pending rather than Read failed. A child whose required reads succeeded remains Current. Connect failed still means TCP establishment failed; Read failed means no valid readings were obtained in the current poll. Retained values from previous polls do not count as current successes. Pending leaves dataValid false and preserves underlying failures in lastError, with per-reading validity and timestamps unchanged.


## 0.2.6: explicit device display status

Successful live snapshots now say Online instead of Current. getDeviceDisplayStateId explicitly selects status for all three device types, matching the intended XML selection, rather than allowing a thermostat's temperature display default to produce a blank column when no measured room input is available. Startup already calls stateListOrDisplayStateIdChanged, so existing devices are refreshed without recreation. Native thermostat temperature and setpoint fields remain separate. Simulator labels and Pending/Read failed/Connect failed are unchanged. The native UI result still requires owner confirmation after installation.

## Owner UI check of 0.2.6 — 6 November 2026

The owner screenshot shows live heating status Online, dataValid true and roomSetpoint 22, but an empty device-list State column. DHW displays its measured temperature. The installed plugin contains the explicit display-state callback. A read-only check of the saved Indigo database also confirms the heater has DisplayStateId=status, NumTemperatureInputs=0 and an empty temperatureInputsAll. Therefore the 0.2.6 override did not fix the native Mac thermostat row. Evidence points to thermostat-specific rendering of its temperature summary, but the client implementation has not been verified. Do not claim this is fixed, fabricate a measured room temperature, or put a setpoint into a measured-temperature field. The generic system status display and child custom status states still work. Live connector access was unavailable during investigation. The stale actionStatus “Simulator readback confirmed” in the live screenshot is historical and is another presentation issue, not evidence of a live write.


## 0.2.7: separate system connectivity from completeness; native display evidence

A system snapshot with any valid current-cycle reading now reports Online and clears the device error banner, even when dataValid remains false. lastError, per-reading validity, timestamps and lastSuccess (complete success) retain their existing meanings. A new lastAttempt alone is not proof of connectivity, and retained readings do not count. Incomplete children retain Pending, while complete children report Online. Simulator system snapshots retain their SIMULATOR label, including incomplete snapshots with at least one valid value.

Careful native UI investigation printed the live heater's device details to the Indigo event log. The live IOM reports displayStateId=temperatureInputsAll, displayStateValRaw and displayStateValUi empty, temperatures=[], temperatureSensorCount=0, and status=Online. This differs from the saved database's DisplayStateId=status and from our getDeviceDisplayStateId return value. Thus the failure is the native thermostat's effective display-state selection, not a missing Online update. It is unresolved; no fake measured temperature, read-only aggregate update, or use of an error banner to display Online is introduced. The offline test has been renamed to reflect that it verifies status and the requested display ID, not actual client rendering. The existing native callback is retained pending a verified solution. Version increments because the owner has now installed 0.2.6.

## Live native temperature display — 0.2.11

The live heater previously advertised zero temperature inputs, so Indigo's thermostat aggregate display was blank. It now advertises one input and publishes current-cycle boiler temperature to `temperatureInput1`, as provisionally agreed with the owner. This is boiler temperature, not measured room temperature; simulator mode continues using its synthetic room measurement. Heater custom states now include boilerTemp, boilerTempValid and boilerTempUpdated. Heater snapshot validity requires both boiler and room-target readings; missing boiler data retains the previous temperature with invalid/pending/error diagnostics rather than substituting a setpoint. Both thermostat children request native `temperatureInputsAll` display, while the system retains status.

The setpoint arrows remain simulator-only because physical writes are unverified and blocked. Consequently the live native pane does not have the same editable controls as the simulator. This is separate from the fixed missing-temperature issue. Existing device properties migrate on the next poll; deletion/recreation is not required for this change.

Offline validation: 28 tests passed, including simulator-to-live capability changes, correct boiler versus room/setpoint mapping, and retained-but-invalid boiler readings after failure. Installer packaged successfully. The Indigo connector was unavailable (429), so native rendering on owner devices 1374820063 and 462295338 still requires owner confirmation after installing from GitHub.
