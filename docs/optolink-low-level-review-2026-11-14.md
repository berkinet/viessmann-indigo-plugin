# KO2B low-level Optolink review — 14 November 2026

## Findings that change our understanding

The most useful new evidence was already on the owner's Mac: `/Users/rdp/Downloads/Viessmann/DPDefinitions.xml`, definition version **0.0.26.4683**, dated December 2017. The full dataset links **619 event definitions** to V200KO2B (model row 340, description NR1 2011). This is a service-software definition of expected capabilities, not proof all fields exist or refresh on the installed firmware. Many definitions are aliases, settings, installation-dependent points or actions; this is not 619 newly usable sensors.

Decoded the dataset's extension values as primitive strings, integers, booleans and doubles without instantiating serialized objects. Cross-checked 36 relevant layouts against the separate `Vitosoft XML files/XML/ecnEventType.xml`. The flattened device list in that older separate file has no KO2B entry, so exact-model membership comes from the full DPDefinitions dataset. Curated numeric layout evidence and source hash are in `sources/ko2b-selected-layouts-2026-11-14.json`. The full service catalog was not copied into the public repository.

No controller settings, plugin behavior or live XML were changed during this review. Only existing polling logs were read to correlate owner-supplied events.

## The protocol exposes blocks, not just named commands

vcontrold command names are local XML labels. The usual KW request selects a read function, two-byte address and byte count. A new XML read can request a documented block absent from the existing command list. It does not need a dedicated wire command named after each field. Conversely, increasing the requested length without a known block definition does not establish that adjacent virtual addresses form contiguous CPU memory.

KW's documented function families include ordinary Virtual_READ (F7), GFA_Read (6B) and PROZESS_READ (7B), with corresponding writes. The KO2B catalog entries examined use ordinary Virtual_READ for the promising status fields. No model-specific evidence was found that switching to GFA/process reads would expose this Siemens LMO's LED state. GFA refers to a gas firing-control family; it must not be treated as a generic tunnel into the installed oil-burner control.

P300 additionally has framed, checksummed replies, error messages and remote procedure calls. Our installed production configuration uses KW2. P300 support on this exact installation was not tested during the review. Changing transport would not manufacture an absent flame datum; it could make unsupported reads easier to distinguish. No published automatic enumeration/read-all operation was found that returns every supported controller field.

Of the 619 model-linked definitions, 589 have Virtual_READ, 21 have Remote_Procedure_Call, eight have no read function and one says undefined. The RPC entries are reset/configuration/history-clear actions or LON participant-list operations, not a hidden flame-state service. Some resets even have an FCRead entry: the word read in metadata is not sufficient to establish side-effect-free RPC behavior. None was invoked.

Sources:
- https://github.com/openv/openv/wiki/Protokoll-KW
- https://github.com/openv/openv/wiki/Protokoll-300
- https://github.com/gismo2004/VExtractor (catalog extraction model; inspected at 2c90c4f562f7f5f9af8b2f73ece9d5589d4caa56)
- https://github.com/gismo2004/optov/blob/2bd0dbab539eb6a233c752efa0586c0ed4ad68c7/docs/protocols.md

## Exact layouts: offsets matter

All byte offsets below are zero-based. Bit masks use MSB-first numbering within each byte, bytes in wire order. This convention is implemented by the inspected OptoV decoder and agrees with our existing relay mask, but physical-state meanings still need installation-specific validation.

| Existing command / field | Catalog block | Relevant layout | Consequence |
| --- | --- | --- | --- |
| getProbeBurner1 | One byte | DigitalAusgang_Brenner; enum 0/1 | A defined digital output, not a documented flame-sensor input |
| getProbeOutputStatus | Two bytes | Byte 0 divided by two; byte 1 enum 0/1 | Confirms the new output/status layout; does not independently establish combustion |
| getProbeProductionStatus | **Four bytes** | Fault: byte 2 mask 04; hard block: byte 2 mask 01; special operation: byte 2 mask 08; storage charging: byte 1 mask 02 | Our earlier one-byte read omitted the relevant error/block fields entirely |
| getProbeAlarmHeader | **29 bytes** | Fault code at byte 28; participant byte 15; affected participant byte 27; change flag byte 14 mask 10; fault-manager role byte 14 mask 20 | A one-byte header cannot answer the alarm-code/change questions |
| getProbeRelayStatus | Two bytes | Collective fault: byte 0 mask 01; burner relay: byte 0 mask 02 | Existing mask has catalog support, but the collective-fault relay is not necessarily a persistent actual-fault flag |
| Boiler output value (no new command installed) | Two bytes at A305 | Output at byte 0, divide by two | Alternative model-linked output, primarily relevant to modulating configurations; lower priority for our single-stage burner |

Catalog identifiers for the four-byte production structure name the fault field `nvoProdCState_Fehler_CFDM` and hard block `nvoProdCState_HarteSperre_CFDM`. Its descriptive text means at least one boiler has a fault, and at least one boiler is signed off, respectively. **Hard block is not yet proven to mean Siemens safety lockout.** These are LON-facing production/plant concepts exposed through virtual reads; do not substitute their names for validated burner semantics.

The 29-byte alarm block also contains date/time components (year at bytes 16–17, month 18, day 19, hour 20, minute 21, second 22). Their encoding and endianness need confirmation before publishing decoded timestamps. The change flag indicates a change, not necessarily an active alarm; an alarm record may remain historical. A complete read should be correlated with fault acknowledgement and recurrence.

## Why the current relay interpretation can clear too early

The KO1B/KO2B service manual, document 5727177 DE 9/2023, page 65, states that acknowledging a fault switches off the collective fault-signalling output. If the fault remains, the notification and output are reasserted the next day.

That provides a supported explanation for a collective-fault relay bit clearing while the burner remains locked out. The bit is useful as an observation of that output; treating its clear state as proof that the underlying burner fault has cleared is too strong. No plugin change was made as part of this research.

https://community.viessmann.de/viessmann/attachments/viessmann/customers-gas/124737/1/5727177VSA00007_1.pdf (page 65)

## Flame versus output and runtime

The exact-model catalog explicitly calls getProbeBurner1 a digital output and defines OFF/ON. This gives substantially stronger evidence than inference from observed 00/01 alone, but not a promise that it is flame feedback. It also confirms the first/second-byte layout of getProbeOutputStatus; its label is actual system output, which still needs interpretation during burner lockout.

No explicit flame, ionization or burner-phase field was found among the 619 model-linked event identifiers. Other families do contain explicit flame/phase entries, as recorded in flame-feedback-research-2026-11-14.md. Their existence elsewhere does not establish KO2B availability. Absence in this dated catalog is not proof the firmware exposes no undocumented equivalent. The getStatusFlamme candidate returned FF twice in the separately authorized earlier experiment.

Do not assume rising burner hours prove flame. The KO2B manual page 49 explains that, when the B4 signal is unavailable, runtime is estimated from the burner start/demand signal with a configurable startup delay subtraction. It explicitly describes runtime continuing while a mechanical temperature regulator stops the burner but demand remains. We have not established whether the installed wiring/firmware uses B4 feedback or estimated counting. Merely observing hours rise would not settle that question.

https://community.viessmann.de/viessmann/attachments/viessmann/customers-gas/124737/1/5727177VSA00007_1.pdf (page 49)

The Siemens LMO64.301C2V LED/OCI400 interface is separate. No verified Optolink tunnel to its color codes, flame current or diagnostic stream was found.

## Owner log correlation, Paris local time

Raw daemon log uses UTC; add one hour for the owner's November Paris timestamps. On 14 November:

| Paris time | getProbeBurner1 | getProbeOutputStatus | getProbeRelayStatus |
| --- | --- | --- | --- |
| 12:02:04–08 | 00 | 00 00 | 80 20 |
| 12:03:12–16 | 00 | C8 01 | 80 20 |
| 12:04:20–24 | 01 | C8 01 | 82 20 |
| 12:11:10–14 | 00 | 00 00 | 80 20 |
| 12:13:19–23 | 00 | 00 00 | 80 20 |

Readings in each row were sequential, not simultaneous. At 12:03, two seconds separated the zero burner-output flag and 100% plant-output reply. That could reflect different signal stages or a real state change between requests; it does not prove an eight-byte-frame or stale-cache problem. Both signals fell before the getStatusFlamme diagnostic started at 12:12:10, so that interruption did not cause the observed fall at 12:11. The burner relay bit in the packed relay state agrees with getProbeBurner1 in these samples; it is not independent flame evidence.

The owner's trigger time and a last-success timestamp can differ. For example the 12:12:10 log message refers to a 12:11:12 reading. Do not align a trigger's outer log timestamp as if it were a fresh physical measurement without checking the embedded state timestamp.

## Recommended next investigation

1. Read getProbeProductionStatus as the documented four-byte block, preserve raw bytes, and decode the specific fault/block bits beside the existing relay/history observations.
2. Read the complete 29-byte getProbeAlarmHeader block, retaining code, change flag and participant information before interpreting clear/active semantics.
3. Compare those fields through an ordinary demand-off/start/fault/acknowledgement sequence when events happen naturally. No deliberate fault or extra reset is required.
4. Compare the model-linked boiler-output alternative only if the first two steps leave a useful question unanswered.

These reads require correct XML lengths and serialized optical ownership. They have not been installed or run in this research turn. The report identifies concrete candidates and their exact layouts; it does not claim that either block supplies actual flame or that its catalog bit meanings have already been verified on the installed unit.
