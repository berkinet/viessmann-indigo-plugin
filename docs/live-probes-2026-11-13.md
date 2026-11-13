# Live KO2B candidate probes — 13 November 2026

Owner explicitly authorized live read-only candidate testing after reporting the heater running. Metadata: `V200KO2B (ID=209F) (Protocol=KW2)`. No setpoint or other physical write was issued in this probe session. The optical protocol necessarily transmits read requests; "read-only" refers to controller operations, not passive listening.

## Verified measured room temperature

`getProbeRoomTemp`, address `0896`, two bytes with UT signed-short /10 decoding, returned **20.600000 C at 13:37:06 UTC**, then **20.700001 C at 13:39:37 UTC**. The owner independently confirmed the room display had been 20.6 and was now 20.7. This verifies the measured-room mapping on this installed KO2B, not merely a plausible value from another model. The trailing decimal noise is float formatting. The companion `089C` probe returned raw `00`; its enumeration has not been decoded.

The plugin's native heater temperature still uses the provisional boiler-temperature mapping introduced in 0.2.11. This research does not silently change that display mapping or add the candidate read to periodic polling.

## Named status reads

| Command | Address / requested bytes | Response | Interpretation limit |
|---|---|---|---|
| getBoilerTemp | 0802 / 2 | 60.4 C initially; 59.6 before status batch, 61.1 after | Working known-reading baselines |
| getProbeRoomSensorStatus | 089C / 1 | 00 | Companion room-sensor status enum unknown |
| getProbeProductionStatus | A395 / 1 | 00 | First production-state byte; error/lockout field offsets/masks unknown |
| getProbeRelayStatus | A152 / 2 | 82 80 | Two raw relay-state bytes; bit mapping unknown |
| getProbeAlarmHeader | A132 / 1 | 00 | First byte only, not the full alarm/error-code structure |
| getProbeBurnerFault | 0884 / 1 | 00 | Cross-model candidate responds; current-fault semantics unverified |
| getStatusStoerung | 7579 / 1, existing RT decoder | UNKNOWN | Still not a useful decoded system-status read |
| getProbeProgram | 2323 / 1 | 02 | Raw value; no new mode/write inference |

The status probes returned bytes with valid known-temperature reads around them. This is evidence of responding addresses under the current conditions, not proof that zero means no fault or that the relay bits have any particular meaning. No controlled fault or power-state test was performed. A395 remains a possible compact status/health read, but its semantics and behavior on controller failure need verification before adopting it as a generic system status.

## Raw-path comparison and limitations

A first raw-script batch read the known 0802 baseline as `05 05`, room candidate as `05 05`, and timed out at 089C. The batch stopped there. Those bytes are unusable as datapoint evidence; the failed known baseline prevents interpreting the candidate output. Existing named commands then returned sensible boiler and room readings. Subsequent tests used the daemon's compiled named-command path. The cause of the raw-path discrepancy was not established and is not attributed to unsupported datapoints.

## Configuration and reproducibility

Five additive getaddr-only definitions were inserted into the existing live `/etc/vcontrold/xml/revtest.xml`: getProbeRoomSensorStatus, getProbeProductionStatus, getProbeRelayStatus, getProbeAlarmHeader and getProbeBurnerFault. They use the address/length pairs in the table, explicit device ID 209F, and no decoder unit for raw status bytes. Backup: `/etc/vcontrold/xml/revtest.xml.before-status-probes-20261113`. Existing symlinks and setters were unchanged. The daemon's `reload` command acknowledged the updated XML; no service restart was needed.

[Command inventory](command-inventory.md) lists the 163 XML definitions with 209F field overrides; [loaded commands](sources/loaded-commands-2026-11-13.txt) records the daemon's actual 148-command listing. Neither list alone proves live support. Detailed timestamps and responses are retained in the three `sources/live-probes-2026-11-13-*.json` files.

No release or push was performed: the owner's hold on publishing the pending-set message remains in effect. That unrelated display implementation is local and passed 35 offline tests.

## getSystemTime health-check validation

The deployed definition is getaddr at 088E, length 8, unit TI (systime), with no 209F override. Two reads on the physical KO2B succeeded and optical release was acknowledged:

| Read | Returned controller clock | Command response duration |
|---|---|---|
| 1 | 2026-11-13T14:33:33+0000 | 2.733 s |
| 2 | 2026-11-13T14:33:45+0000 | 9.262 s |

Requests began at 13:44:24.250 and 13:44:30.051 UTC; received clock values advanced 12 seconds, consistent with elapsed receipt times. The getSysTime decoder in the installed-source lineage takes all calendar/time fields from the eight received BCD bytes, but supplies timezone/DST context from the Pi. Thus the +0000 suffix is host formatting, not proof of the controller's timezone. The controller wall clock appears roughly 11 minutes behind Paris local time during this test; no clock adjustment was made.

Conclusion: getSystemTime is now verified as a responding, advancing controller-clock read for this installation and a suitable candidate for communication-health checks. It does not prove the burner is fault-free, and its observed latency was variable rather than instantaneous. Do not require strict agreement with host wall time as a health criterion. Raw result metadata is saved in sources/system-time-2026-11-13.json. No setter was issued, no polling logic was changed, and publication remains on hold.

## Owner-confirmed D1 state

The owner subsequently reported the burner stopped with active D1 while the controller remained electrically on, and authorized fault/clock reads. No reset, setter or power operation was issued.

| Read | Response during owner-confirmed D1 |
|---|---|
| getSystemTime, first | 2026-11-13T14:36:25+0000 |
| getSystemTime, last | 2026-11-13T14:37:23+0000 |
| getError0 | 2026-11-13T14:30:08+0000 Burner Fault (D1) |
| getProbeRelayStatus (A152/2) | 83 80 |
| getProbeProductionStatus (A395/1) | 00 |
| getProbeBurnerFault (0884/1) | 00 |
| getProbeAlarmHeader (A132/1) | 00 |
| getStatusStoerung | UNKNOWN |

The clock advanced 58 seconds across this batch and all requests released the optical connection successfully. Thus getSystemTime remains useful for communications health while the burner is stopped with D1; communications health must not mean fault-free equipment. getError0 decodes D1 correctly, but remains an error-history record, not independently an active-fault indicator.

A152 changed from the earlier 82 80 sample to 83 80: XOR 01 00, bit 0 in the first byte. This is a candidate for correlation, **not yet a verified fault flag**. Importantly, the D1 record's 14:30:08 controller timestamp precedes the earlier clock reads at 14:33:33/45. Consequently the earlier probe batch cannot safely be treated as a confirmed fault-free baseline; it may already have been in D1, and the relay change may represent a pump or another output. A comparison after the owner confirms D1 has cleared is necessary before assigning fault semantics. Single-byte zeros at A395/0884 and the first alarm byte do not establish absence of fault. Full structure layouts remain unknown.

Detailed data: sources/d1-probes-2026-11-13.json. All findings remain local under the owner's publication hold.

## Existing current-mode commands

At owner request, inspected and read getCurrentMode (2301/1/BA) and getCurrentMode2 (3301/1/BA), with a successful getSystemTime baseline. Both returned `Heating and Warm-Water`; separate getProbeProgram at 2323 returned raw `02`. The existing BA enum maps both raw 03 and 04 to that same text, so these decoded responses cannot distinguish those bytes. Its legacy enum has not been validated against this KO2B. The 23xx/33xx addresses follow circuit-1/circuit-2 families, not two independent fault flags; a returned value at 3301 does not establish installed circuit-2 equipment.

The owner had reported active D1 earlier; no new independent fault-clear observation was available during this batch. These labels therefore do not establish fault-free operation or current-fault clearance. No settings, XML, operating program or setpoints were changed. Responses and timestamps are in sources/current-mode-probes-2026-11-13.json. Publication remains on hold.

## Burner-status comparison

getBrennerStatus uses 551E/1/RT for 209F (the 2053-specific 22/bit1 override does not apply). RT recognizes only 00 and 01. Live response was UNKNOWN. The separately defined getProbeBurner1 at 0842/1 returned raw 01. The exact-model datapoint list labels 0842 as digital burner-stage-1 output; this is more model-specific evidence than the generic 551E definition, but a command/output state is not independent proof of flame or fault clearance. The owner had not newly confirmed whether D1 was still present during this later batch. No inference of active/cleared fault is made from these values. Results: sources/burner-status-probes-2026-11-13.json. No writes, configuration changes or publication.
