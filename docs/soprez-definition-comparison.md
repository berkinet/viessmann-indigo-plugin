# Soprez KO1B/KO2B definitions versus ours — 6 November 2026

## Scope and provenance

The referenced [Soprez project](https://github.com/Soprez/viessmann-optolink-ha) has **no XML files** at the examined revision. It uses an Optolink-Splitter Python poll-list configuration. A textual XML diff would therefore be misleading; this is a semantic comparison of address, byte length, conversion, and read/write role.

Compared its [poll list](https://github.com/Soprez/viessmann-optolink-ha/blob/c313715de8ff313b45fef1a3e2cbc3228a9e28c3/optolink/poll_list.py.example) and [address notes](https://github.com/Soprez/viessmann-optolink-ha/blob/c313715de8ff313b45fef1a3e2cbc3228a9e28c3/docs/addresses.md), pinned to commit c313715de8ff313b45fef1a3e2cbc3228a9e28c3, against our current deployed command XML /etc/vcontrold/xml/revtest.xml and unit conversions from /etc/vcontrold/daemon-config/vcontrold.xml. Read configuration files only; no controller requests, serial access, service changes or XML writes. The comparison resolves device ID 209F overrides rather than comparing generic defaults. The normalized input containing commands/units/device names has SHA256 06f13b1774183b7c14c8eed5564373ea715eed9620d81c494b0b782d1ca6e7ff.

His claimed installation: Vitorondens 222-F, labelled KO1B/KO2B, **20CB / P300**. Ours: **209F / KW2**. Same advertised family is not proof of identical registers or write semantics. The snapshot contains 27 poll entries and 158 command definitions on our side; these counts do not measure verified support. His validation claims are not independent confirmation on ours.

The [complete 27-row comparison CSV](sources/soprez-comparison.csv) records every poll entry, including matching command names, lengths and active conversion definitions. It does not execute his Python configuration.

## Most useful differences

| Function | His definition | Our effective 209F definition | Assessment |
| --- | --- | --- | --- |
| Measured room temperature | 0896, 2 bytes, signed ×0.1 | getProbeRoomTemp: 0896 / 2 / UT signed short ÷10 | Same candidate and conversion; already prepared as a read-only probe, not verified on our physical controller. |
| Burner fault | 0884 / 1, unsigned raw code | No same-address read. Existing getStatusStoerung uses 7579 / 1 / RT; history uses 7507 onward / 9 / ES | Important new read candidate for current-fault research. Its “0=none” meaning is the other author's claim, not established on 209F. |
| Status word | A152 / 2, raw | No same-address read | New diagnostic candidate, but bit meanings/active-fault semantics not supplied. |
| Burner output | A38F / 1 / ×0.5 | getBurnerOutput: 55E3 / 1 / PR (short ÷2) | Different address. Our PR type is short despite a one-byte command; worth reviewing separately rather than assuming equivalent output. |
| DHW charging pump | 6513 / 1, raw | getPumpStatusSp: 0845 / 1 / RT | Different address and raw versus 00/01 enum. A functional mapping candidate, not confirmation that both refer to the same physical pump. |
| DHW circulation pump | 6515 / 2, raw | getCircPumpStatus: 0846 / 1 / RT | His own notes call 6515 meaningless, yet his poll list still includes it. Do not copy it as validated support. |
| Burner stage 1 | 0842 / 1, numeric 0/1 | getBrennerStatus: 551E / 1 / RT; getProbeBurner1: 0842 / 1 / raw | Alternative address already covered by our probe. Must decode its raw-hex output deliberately. |
| Burner starts | 088A / 4, unsigned | getBurnerStarts: 088A / 2 / CO int; getProbeStarts: 088A / 4 / raw | Existing normal command is shorter; our candidate already matches the four-byte length. Counter signedness/overflow and raw conversion still need verification. |
| Filtered storage temperature | 0812 / 2 / ×0.1 | getStorageTemp overridden for 209F to 0070 / 1 / UT1 ÷2; getProbeStorage: 0812 / 2 / UT | Effective device-specific override matters; existing probe covers his candidate. |
| A1 flow temperature | 0810 / 2 / ×0.1 | getTempVListM1 lacks an address; getProbeFlowA1: 0810 / 2 / UT | Existing candidate fills the missing definition. |
| Heating curve slope | 27D3 / 1 / ×0.1 | getNeigungM1: 2305 / 1 / UN; getProbeCurveSlope: 27D3 / 1 / raw | Alternate register already present as probe; ours does not automatically apply his scaling to raw probe output. |
| Heating curve level | 27D4 / 1 / signed ×1 | getNiveauM1: 2304 / 1 / ST char; getProbeCurveLevel: 27D4 / 1 / raw | Alternate register already present as probe; signed interpretation remains explicit future work. |
| Full device identity | 00F8 / 8 raw | getDevType: 00F8 / 2 / DT enum | Eight-byte identity may distinguish hardware/software variants. Existing vcontrold `device` metadata is configured identity, not a hardware read. |
| Current DHW target | 6500 / 2 / ×0.1 | No same-address read; getTempWWsoll reads 6300 / 1 / ST | His notes call 6500 unreliable/stale, but the poll list includes it. His 6300 target is already represented on our side. |

## Definitions substantially aligned

Both use 0800/2 for outside temperature, 0802/2 for boiler water, 0804/2 for DHW, 0808/2 for exhaust, and 2544/2 for A1 flow target, all ×0.1. Our UT is signed short; his outside temperature is signed but most other temperatures use unsigned decoding, so these are not entirely identical conversion types. Both read burner hours at 08A7/4 and convert seconds to hours (our CS is uint V/3600; his multiplier is approximately 1/3600).

Both have standard/reduced targets at 2306/1 and 2307/1 and DHW target at 6300/1. Our ST is signed char; his corresponding values are unsigned. Their expected positive ranges overlap, but these are definitions, not proof of identical supported ranges. Our party target 2308 is not included in his poll list.

Both read 2301/1, 2302/1 and 2303/1 for program/economy/party-related information. **The conversions differ:** he exposes raw values, while ours uses BA (labelled operation mode) and RT (00/01 else UNKNOWN). Our BA labels must not be treated as validated mode encodings on this controller. Our getProbeProgram already covers his 2323/1 program register as a raw read.

## Write definitions — compare, do not apply

His writable entities cover 27D3 (slope), 27D4 (level), 2306/2307 (room targets), 6300 (DHW target), and 2323 (program). Our existing slope/level setters instead target 2305/2304 and our program setter targets 2301; our 27D3/27D4/2323 entries are deliberately read-only probes, not new setters. Room and DHW target addresses align. His room-target UI limits are 10–30 C, while our simulator trial permits 3–37 C; neither establishes our physical-controller limits.

His notes say program writes to 2301 fail and economy/party writes can be acknowledged but ignored on 20CB. Those are important cautions for later tests, not proof that our 209F behaves the same. His program UI exposes only DHW-only and heating+DHW; its warnings about numeric value 3 are controller-specific and must not replace our as-yet-unverified mode map.

**Our plugin still blocks all physical writes. Nothing was changed or tested as a result of this comparison.**

## What ours contains beyond his poll list

Our XML also defines fault history, the general 7579 fault read, party targets, additional pumps/mixers/circuits, solar information, weekday timer blocks, time-setting commands and various exploratory reads. Their presence in XML is not support verification. His list is not a comprehensive superset and does not provide a replacement for our device-specific configuration. Several of our old commands may be inapplicable; the owner prioritizes finding missing useful support rather than removing every unsupported definition.

## Recommended next-week read-only priorities

1. Compare 0896 with the actual room controller's measured temperature.
2. Evaluate 0884 as the best newly identified current burner-fault candidate; compare healthy and faulted observations if safely available, retaining raw byte values. History D1 alone remains insufficient.
3. Record A152 raw status without inventing bit meanings.
4. Test A38F and 6513, then the already-prepared 0842/0810/0812/088A/27D3/27D4/2323 probes as useful and safe after repair.
5. Consider an eight-byte 00F8 identity read for exact model/firmware matching. No new probes or XML changes are made by this report.

Do not promote 6500 or 6515 merely because the example polls them: its own notes contradict that interpretation.
