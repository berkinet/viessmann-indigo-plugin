# Flame feedback beyond LED names — 14 November 2026

Research only. No new physical query, diagnostic-mode activation, reset or controller write.

## Other Viessmann controllers

A scan of the pinned ViessData21 DP_Listen_2.zip archive (80a2a8cf6e0506edcb93fd39659f044bc88a4c17) found explicit Flammensignal/GWG_Flamme1 byte entries at 55DD in VDensHC1/HC2/HO1, VPend, VPlus and VScot families. Older GWG lists expose Betriebsphase des Feuerungsautomaten/GWG_Betriebsphase at 009E. The KO2B list has no matching explicit flame/phase entry under these terms; this is not proof none exists. Its getProbeBurner1 field is named DigitalAusgang_Brenner, supporting an output interpretation.

Community examples call flame reads getStatusFlamme or getVitoStatusFlamme. Some use 55DD, others 55DE, with enum 00=off, 0B=on. These are different model mappings and no complete/verified KO2B enum was found. A 2025 Vitodens owner first reported always-on flame status, then said they got flame status working, without documenting a reproducible final mapping. Another response proposed 55D3, a field also reported elsewhere as modulation; do not conflate these addresses or copy the enum to KO2B.

Sources:
- https://github.com/philippoo66/ViessData21/blob/80a2a8cf6e0506edcb93fd39659f044bc88a4c17/DP_Listen_2.zip
- https://community.viessmann.de/t5/Gas/Device-ID-Vitodens-200-aus-Ca-2011/m-p/589603 (search returned thread text; direct page retrieval failed)
- https://forum.iobroker.net/topic/2715/viessmann-adapter/180?page=11 (getVitoStatusFlamme example)

## Native KO2B structures still worth decoding

The model list names multiple fields in getProbeProductionStatus: hard lockout, error, special operation and storage charging, all sharing the A395 base. Our earlier single-byte 00 read does not decode that structure and cannot eliminate it. Offsets/lengths/bit meanings remain unverified. getProbeAlarmHeader likewise has a structured alarm/change payload, not a complete alarm verdict from one byte. These structures may improve error-state determination without exposing flame itself.

## Separate Siemens diagnostic interface

Siemens OCI400 datasheet N7614 explicitly describes data transmitted through the red LED in the LMO lockout reset button, received by an optical head and delivered via RS-232 to ACS410 software. This is a separate hardware/protocol endpoint, not the Vitotronic Optolink port and not a currently available vcontrold command.

The LMO14/24/44 datasheet N7130 documents interface diagnosis after lockout and blink-code selection. During fault diagnosis the control outputs are off and the burner remains off. Consequently do not assume OCI400 is an always-on flame monitor for the installed variant. Older ACS400 documentation distinguishes UDS diagnostic delivery in fault position from eBus-equipped variants with broader data access. Exact installed LMO model and supported interface mode must be verified before recommending hardware/software.

Primary sources:
- https://sid.siemens.com/api/khub/documents/hbPAy1lgqsIKyhSA3s3Brw/content (N7614, 19 May 2016)
- https://community.viessmann.de/viessmann/attachments/viessmann/customers-oil/33474/1/n7130de.pdf (N7130, 18 May 2016, pp 12–13)

## Conclusion

An explicit flame signal exists in other Viessmann systems, so the broader search is productive. getStatusFlamme/getVitoStatusFlamme are candidates for a controlled raw read/transition comparison, not established KO2B capability. The Siemens LED has a real diagnostic data path, but continuous operation and compatibility are unresolved. Continue prioritizing exact KO2B structure evidence and preserve unknowns; do not infer flame from burner output alone.

## Nameplate confirmed by owner photograph

The owner's 14 November photograph identifies the installed burner control as Siemens **LMO64.301C2V**, Siemens order code **S55333-B402-A100**, Viessmann **VI9668559**. Label supply: 230 V AC, 50–60 Hz; TSA max 10 s, t8=90 s. Photo source: /Users/rdp/Desktop/Screenshots/Siemens-burnet-controller.jpg. A still photograph shows green illumination but cannot establish steady versus flashing. Earlier LMO14 identification was an assumption from a family manual and is superseded.

Siemens LMO64 datasheet CC1N7138en explicitly supports OCI400/ACS410 and describes unidirectional UDS transmission of operational status, faults and service information in diagnostic mode. Compatibility at family level is now supported; continuous normal-operation capture and exact Viessmann variant behavior remain unverified. Primary document: https://sid.siemens.com/api/khub/documents/TYtoZZmW~TAs9jeFy7WJAg/content .
