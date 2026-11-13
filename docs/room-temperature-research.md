# Measured room-temperature research — 6 November 2026

## Finding

Other owners do report actual measured room temperature through Optolink. The strongest candidate for this project remains 0x0896, now supported by explicit user observations rather than an address-table label alone. None of these sources proves support on this installation's 209F/KW2 controller. No Pi access, controller reads, XML edits, or boiler writes were performed for this research.

## Prioritized candidates

| Address | Reported length / interpretation | Evidence and applicability |
| --- | --- | --- |
| 0896 | 2 bytes; temperature multiplied by 0.1. The newer poll list marks signed decoding. | First priority. A KW1 owner with Vitotrol 300 explicitly reports reading room actual temperature here. A separate Vitorondens 222-F integration labels this display-validated on its KO1B/KO2B installation, but identifies device 20CB and P300, not our 209F/KW2. |
| 0898 | 2 bytes, /10; filtered M2 room temperature | Secondary circuit-specific lead in OpenV's table and owner discussion. We have only one heating circuit confirmed; do not assume M2 is relevant. |
| 089A | 2 bytes, /10; filtered M3 room temperature | Table-only, low priority. No owner confirmation located in this pass, and no M3 circuit established here. |
| 0116 | 2 bytes, UT temperature conversion | Different-family lead: a shared vcontrold XML for device 204D defines getTempRaumIst as measured HK1 room temperature. A definition is weaker than a demonstrated successful reading, and 204D is a heat-pump controller. |
| 01D6 | Request 3 bytes; first two little-endian temperature /10, third status interpretation unresolved | Different-family lead with explicit measured evidence: a WO1C discussion includes reply 01 01 80 and a matching Vitotrol reading 25.7 C. Requests for the wrong length can fail. Do not blindly discard the third byte or treat invalid/missing-sensor records as real temperatures. |

The existing read-only getProbeRoomTemp definition already targets 0896 / length 2 / UT. This research strengthens the case for testing it; it is not a new verification of that definition on the physical boiler. Simulator room temperature is synthetic evidence only.

## Primary sources

1. [KW1 owner with Vitotrol 300, FHEM discussion, post 1631, 9 January 2021](https://forum.fhem.de/index.php?topic=20280.1620). Reports retrieving room actual temperature at 0896. The following post describes two 20 C readings without a Vitotrol, demonstrating why plausibility alone is insufficient. This is a different controller from ours.
2. [Soprez address table](https://github.com/Soprez/viessmann-optolink-ha/blob/main/docs/addresses.md) and [poll list](https://github.com/Soprez/viessmann-optolink-ha/blob/main/optolink/poll_list.py.example). The author defines validated as checked against the controller display on a Vitorondens 222-F. The poll list reads temperature_ambiante at 0896, length 2, multiplier 0.1, signed. Treat this as an author's validation claim, not independent confirmation or evidence that all KO1B/KO2B variants share addresses. Their explicit identity/protocol differ from ours.
3. [OpenV address table](https://github.com/openv/openv/wiki/Adressen). Lists filtered room temperatures at 0896/0898/089A for several families. Its measured-room-temperature cell for the 209F KO1B/KO2B column remains blank. Blank means undocumented, not disproved.
4. [WO1C owner report of three-byte temperatures](https://github.com/openv/openv/issues/480#issuecomment-1364274127), [follow-up on unresolved status-byte handling](https://github.com/openv/openv/issues/480#issuecomment-2395545324), and [Vitotrol display comparison, 27 June 2025](https://github.com/openv/openv/issues/480#issuecomment-3012114117). The last supplies the 01 01 80 -> 25.7 C example. The third byte's complete semantics remain unverified; these are heat-pump-family observations.
5. [Shared 204D XML, getTempRaumIst at 0116](https://community.viessmann.de/viessmann/attachments/viessmann/customers-connectivity/45542/1/vito.xml.pdf). Configuration example only, not a report of actual success on our model.
6. [Richard's 2018 KO2B discovery issue](https://github.com/openv/openv/issues/409). Relevant recovered history: owner berkinet already reported wrongly identified room-temperature addresses, successfully recognized the system in Vitosoft, and discussed matching device definitions. Replies recommend correlating device identification with ecnDataPointType.xml and related type/encoding files. This is a model-specific research route if 0896 fails, not a resolved room-temperature address.
7. [ViessData identity mapping](https://github.com/philippoo66/ViessData21/blob/master/DataPoints.txt) and [identification explanation](https://github.com/philippoo66/ViessData21/blob/master/DataPoints_ReadMe.txt). Includes 209F -> V200KO2B and explains that some controller definitions depend on hardware/software identity bytes, not just the first two ID bytes. The file is an identity selector, not a room-temperature register table.

## Distinguish actual temperature from similarly named data

Room setpoint commands are not measured room-temperature sources. In particular 2306/2307/2308 are our standard/reduced/party targets; 2000/2001/2022 are targets on another controller family. The existing roomTemp variable reads getRoomTempSP. No successful temperature-shaped response should be promoted to measured room temperature without corroboration.

The owner's Vitodata screenshot already shows a measured A1/M1 room temperature distinct from these targets, so the controller/system has such information. The unknown is the correct Optolink-accessible representation and its freshness/validity. Exact installed remote/sensor model and source are not yet recorded.

## Deferred validation after repair

Start with the existing 0896 candidate and raw bytes, comparing repeatedly with the actual wall controller/room display (and allowing for filtering). Check that the value follows real temperature rather than the selected target. Do not change setpoints merely to test this. Preserve sentinels and reject fixed defaults or unsupported responses. If unsuccessful, use complete controller/remote identification and device-definition evidence to prioritize alternatives; do not indiscriminately scan registers or claim cross-family addresses as supported. Keep the current heater display source provisional until a measured-room read is verified.

## Live confirmation — 13 November 2026

The installed KO2B returned measured room temperature at 0896 through getProbeRoomTemp: 20.6 C, then 20.7 C. The owner independently confirmed the same change on the room display. This upgrades 0896/2 with UT decoding from candidate to verified measured room temperature for this installation. Companion sensor-status 089C returned 00, but its enum remains undecoded. See live-probes-2026-11-13.md for raw evidence and limits. No plugin display/poll mapping was changed by this research.
