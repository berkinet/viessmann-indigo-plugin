# Production-fault override — 0.2.26

Owner requested a narrow display rule after the captured D1 on 15 November:
productionFault True forces derived burner Off; otherwise keep the existing
burnerOutput > 0 algorithm. productionFault already exists as an independent
system Boolean, decoded from getProbeProductionStatus byte 2 mask 04.

New system states:

- burnerOn: derived Boolean for burner displays, with the productionFault override.
- burnerOnValid: false when existing communication/output validity prevents a
  determination; the previous Boolean is then retained. A reported production
  fault forces Off even if output is unavailable. Communications failure remains
  unknown rather than being reclassified as confirmed Off.
- alarmChangeFlag: Boolean extracted from validated alarm byte 14 mask 10.
- alarmChangeFlagValid: false when the alarm block cannot be decoded; last Boolean
  is retained. Timestamp changes in the block do not change this Boolean.

The reported productionFault value is the override, including its retained value
on a failed status read. Existing productionStatusValid remains available for
investigation; it is not an added prerequisite for using the previous output
algorithm. Clearing the reported fault restores output-based behavior.

Raw burnerOutput, burnerActive, productionFault and alarmBlock are unchanged.
The system device icon follows the derived burner state, with its existing error
icon priority preserved. This is a display policy, not physical flame proof or
an operating control. It never starts, stops or resets the heater.

Change owner-managed logging triggers from alarmBlock to alarmChangeFlag to avoid
logging every alarm timestamp update. Both true and false transitions can be
logged; changeFlag is not the maintained fault condition. No trigger was edited
on the owner's behalf. Control-page work remains paused; its existing flame
image still references raw burnerOutput and should be rebound to burnerOn when
page work resumes after installation.

Release includes the previously published 0.2.25 party changes. The owner installs
from GitHub; no local plugin installation or physical writes were performed.
Regression coverage checks fault override/clear, unchanged raw readings, unknown
output/communications, independent alarm timestamps and validated flag parsing.
