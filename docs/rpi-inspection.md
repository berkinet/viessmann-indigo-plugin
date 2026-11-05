# Raspberry Pi inspection — 5 November 2026

Read-only SSH inspection found vcontrold active under vcontrol.service, using /usr/local/sbin/vcontrold. /etc/init.d/vcontrol supplies no daemon arguments. The following are deployed-file observations; which files the already-running process loaded has not independently been proven. No TCP application commands or boiler writes were sent, and no Pi files or services were changed.

## Configured identity and decoding

/etc/vcontrold/vcontrold.xml selects device ID 209F. /etc/vcontrold/vito.xml names that device V200KO2B with protocol KW2. This establishes configured identity, not a live controller identification read.

Selected command declarations below use getaddr. Listed fields are base fields unless noted. They are candidates, not live-verified capabilities or confirmed mappings to existing Indigo variables.

| Command | Address | Bytes | Unit | Candidate meaning |
| --- | --- | --- | --- | --- |
| getOutsideTemp | 0800 | 2 | UT | Outside temperature |
| getBoilerTemp | 0802 | 2 | UT | Boiler temperature |
| getWaterTemp | 0804 | 2 | UT | Hot water temperature |
| getExhaustTemp | 0808 | 2 | UT | Exhaust temperature |
| getRoomTempSP | 2306 | 1 | ST | Likely normal heating room setpoint, not measured room temperature |
| getTempWWsoll | 6300 | 1 | ST | DHW setpoint |
| getBrennerStatus | 551E | 1 | RT | Burner status |
| getPumpStatus | 2906 | 1 | RT | Pump; circuit mapping unverified |
| getPumpStatusSp | 0845 | 1 | RT | Storage charging pump |
| getCircPumpStatus | 0846 | 1 | RT | Circulation pump |
| getBurnerOutput | 55E3 | 1 | PR | Burner output |
| getStorageTemp | 70 | 1 | UT1 | Explicit 209F override; differs from base 0812/2/UT |

UT declares short, V/10, entity C. PR declares short, V/2, entity %. ST declares char with identity conversion and no entity. RT maps byte 00 to text 0, byte 01 to text 1, everything else to UNKNOWN.

The PR conversion can numerically explain 127.5 as 255/2, but no raw value was read and this does not establish whether 255 is a valid reading, sentinel, or bad address/decoding. RT could explain UNKNOWN for non-00/01 responses; actual bytes remain unknown.

getRoomTempSP and setTempRaumNorSollM1 share 2306/1/ST. Do not map this read to a thermostat's measured-temperature state without resolving its semantics and the existing script mapping.

There are 149 command declarations, including 43 with protocmd=setaddr. These counts do not establish supported commands for this controller. getMixerPosition2 is duplicated at 354C and 454C; do not silently assume which declaration the daemon uses. Some definitions have no base address and only another device's override. Review applicability before polling.

## Remaining work

A bounded filename search and script-path inventory under the Pi user's home, /usr/local/bin, and /opt did not locate the Indigo polling scripts. This was not an exhaustive filesystem search. The scripts may execute on the Indigo Mac. Subsequently, the owner supplied the Mac script path; see existing-poller.md for the inspected active mappings.

Next: preserve relevant configuration evidence locally, generate an applicability-aware command catalogue, locate existing scripts, and then validate selected reads through the shared TCP interface. Keep all writes disabled. Runtime version and active configuration-file provenance remain to be established.
