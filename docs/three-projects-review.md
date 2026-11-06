# Detailed review of three Optolink projects

Reviewed 6 November 2026, offline only. No live controller queries or configuration changes.

## Sources and reproducibility

Inspected repository files at these revisions:

- [ViessData21](https://github.com/philippoo66/ViessData21/tree/80a2a8cf6e0506edcb93fd39659f044bc88a4c17): README, device identification instructions, DataPoints.txt and the V200KO2B definition inside DP_Listen_2.zip.
- [Optolink-Splitter](https://github.com/philippoo66/optolink-splitter/tree/4d47ed542c606bc7aea438e52a4e3234ca1a601e): README, KW/P300 transport, poll-list metadata, CSV output and serial logging implementation.
- [OptolinkDuoBlock](https://github.com/vich-667/OptolinkDuoBlock/tree/6512143ddf3884d5647ded1d3b04707f881dd521): README, value configuration, monitor, decoder and protocol implementation.

These are definition/source findings, not measurements on our heater. Scope is the files above, not an exhaustive audit of every release archive or discussion.

## ViessData21: the strongest new evidence

DataPoints.txt explicitly maps `ecnsysDeviceIdent:209F` to `V200KO2B`. Its [DP_Listen_2.zip](https://github.com/philippoo66/ViessData21/blob/80a2a8cf6e0506edcb93fd39659f044bc88a4c17/DP_Listen_2.zip) contains `DP_Listen - Kopie/DP_V200KO2B.txt`. Thus we now have a model-specific Vitosoft-derived list rather than relying only on another owner's KO1B/KO2B description or a different controller family.

The list supplies names, addresses, broad types and UI visibility conditions. It does **not** supply sufficient field offsets, bit masks, scaling or enumeration definitions to implement every entry. Repeated addresses represent structured fields; they must not each be decoded as independent whole-byte values.

| Address | Exact-model definition | Implication |
| --- | --- | --- |
| `0896` | `TiefpassTemperatur_RTS_A1M1`, Int, room temperature A1/M1 | Strongest measured-room candidate; existing read-only XML probe already targets it. |
| `089C` | `HO2B_SensorStatus_RTS_M1`, Byte | Companion room-sensor status; decode enum remains unknown. |
| `0898` / `089D` | M2 room temperature / sensor status | Reference only; does not establish installed M2 equipment. |
| `089A` / `089E` | M3 room temperature / sensor status | Reference only. |
| `2306` / `2307` | Normal / reduced room setpoints, Byte | Confirms these are targets, not measured room temperature. |
| `2500` | Current room target A1/M1, Byte | Distinct from selected normal/reduced target; potential effective-target read. |
| `2323` | Operating mode A1/M1, Byte | Supports prioritizing the existing probe; does not establish numeric enum or write support. |
| `A152` | Relay fields including collective fault, pumps and valves | Potential fault evidence, but shared structured address requires field layout. |
| `A132` | Alarm structure, including error code and date/time fields | Potential fault evidence; current versus historical semantics unproven. |
| `A395` | Production state fields including error and hard lockout | Additional model-specific fault/lockout lead; bit/field layout unproven. |

Room temperature is explicitly hidden when the remote control is absent, its coding is absent/zero, or the HK1 room sensor is absent. This is useful evidence that a plausible numeric value alone is insufficient: we should inspect sensor presence/status and compare with the actual room reading after repair. The list's `Int` label alone does not establish the two-byte signed divide-by-ten conversion; that candidate conversion comes from the separately documented working examples.

No `0884` or `7579` entry was found in this exact-model text. Their absence is not proof of unsupported addresses: the README explicitly warns that extracted lists can be incomplete. In particular, do not replace our existing fault logic with an unverified A152/A132/A395 interpretation.

Recommended later read-only sequence: existing `0896` probe plus `089C`, compare against Vitodata/thermostat, then investigate the structured fault fields with authoritative type definitions or captures. No broad address scan or writes are needed.

## Optolink-Splitter: useful transport and diagnostic patterns

It provides local MQTT/TCP access while mediating access to the physical optical connection, optionally alongside Vitoconnect. This supports our single-owner serialized communications architecture; Indigo logical devices should remain clients of one manager.

Concrete implementation findings:

- `c_polllist.py` carries address, length, scale/type, signedness and optional byte filter separately. Poll-cycle groups allow different update rates. This is a useful future pattern for fast temperatures versus slower counters/configuration, without requiring a new connection per device.
- `c_LoggingSerial.py` wraps serial reads/writes and logs direction and raw hex, with rotating log files. This is a practical reference if we later add bounded raw diagnostics. It records byte chunks; protocol reconstruction must handle split/coalesced reads.
- `optolinkvs1.py` explicitly waits for `05` during KW synchronization. Its initialization first **transmits** `04` and then performs an identification read. It must not be mistaken for our receive-only activity probe.
- `viessdata_util.py` writes weekly CSVs, but substitutes `0` for false/missing values in its export path. We should retain our explicit validity/error/timestamp fields rather than adopt that behavior.
- KW support exists, but the README still qualifies KW plus Vitoconnect compatibility and asks for testers. This is not proof that a splitter installation would work on our exact arrangement.

There is no reason from this review to replace vcontrold or add MQTT now. The useful additions are selective polling and optional directional capture, when justified. Splitter code is GPL-3.0; this review does not copy it into the plugin.

## OptolinkDuoBlock: monitoring and decoding lessons

This is a Python/OpenHAB-oriented heat-pump integration. Its hardware normally permits Vitoconnect communication and uses DTR to block that connection when the PC takes direct control. That is a different deployment from our one-client vcontrold setup.

Concrete implementation findings:

- `vito_monitor.py` decodes P300 read responses, matches configured addresses, and stores both last value and last-update time. With database logging enabled it also records unconfigured response addresses/raw values. That is useful for discovery during another client's normal traffic, not evidence of unsolicited telemetry.
- `vito_data_handler.py` deliberately truncates raw data to the unit's numeric length before conversion. For UT that means decoding the first two bytes, even when configuration requests three. This corroborates the previously observed temperature-plus-status format on other families, but it also discards the third byte without validating it. We should preserve and interpret status rather than silently copying that decoder behavior.
- `value_config.py` contains normal/reduced/party room **setpoints** at `2000`, `2001`, `2022`; it does not establish a measured-room address for our controller. Its heat-pump addresses and generic mode enum cannot be transferred to 209F.
- The separation between passive monitor and active read/write handlers is useful. The monitor explicitly rejects writes. Our existing communications abstraction and simulator gate already address the relevant separation.

The project is MIT-licensed, but no source was copied. Its main value here is the raw-plus-decoded logging pattern and a warning about dropping status bytes, rather than new verified boiler controls.

## Decision

Keep our present architecture. Prioritize the exact-model room sensor pair `0896`/`089C` after repair, and investigate A152/A132/A395 structure definitions before proposing current-fault decoding. Keep the unsolicited-frame conclusion unchanged: these source paths do not establish spontaneous telemetry beyond the separately observed `05` activity. See public-capture-analysis.md for the actual capture evidence.
