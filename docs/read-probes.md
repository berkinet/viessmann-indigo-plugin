# Experimental 209F read definitions — 5 November 2026

Owner authorized editing /etc/vcontrold/vito.xml after creating /etc/vcontrold/vito.xml-bak. The backup matched the live file byte-for-byte before editing, SHA-256 5a93e5ac7f52a308a75451fcdfd679b4383379fc12cb06449301eac80eaf7886.

Nine separately named, 209F-only getaddr definitions were appended. Existing declarations (including all writes) were checked for semantic equality and preserved; device selection, vcontrold.xml, existing conversions, plugin polling and Indigo schedule were not changed. File ownership/mode were preserved; the owner's backup was not overwritten. The resulting live XML hash is b763a75172028039e568a81b86c265110d3ea87a24c6a111427aa88b2f86d243.

| Command | Address | Bytes | Output |
| --- | --- | --- | --- |
| getProbeFlowA1 | 0810 | 2 | UT temperature |
| getProbeStorage | 0812 | 2 | UT temperature |
| getProbeBurner1 | 0842 | 1 | Raw bytes |
| getProbeProgram | 2323 | 1 | Raw bytes; no BA enum assumption |
| getProbeCurveLevel | 27D4 | 1 | Raw bytes; signed interpretation unverified |
| getProbeCurveSlope | 27D3 | 1 | Raw bytes; wiki suggests division by 10 |
| getProbeSolarDay | CF30 | 4 | Raw bytes; solar hardware applicability unverified |
| getProbeStarts | 088A | 4 | Raw bytes; comparison with legacy two-byte counter pending |
| getProbeRoomTemp | 0896 | 2 | UT temperature; lower-confidence cross-model candidate |

See [support-gap report](openv-support-gaps.md) for evidence and qualifications. None is established as working on this heater merely by being registered. Raw output avoids adding guessed decoding or modifying shared conversion units. Oil-consumption scaling remains unchanged for the same reason.

The committed [XML fragment](../config/209f-read-probes.xml) contains only the new definitions; it is **not** a replacement for the full vito.xml and must not be installed over it. The Pi's full XML remains local and is not published.

Validation: Python XML parse; unique command names; getaddr-only additions; original command semantics preserved; metadata-only daemon reload succeeded and all nine names appeared in its command catalogue. No candidate reads or boiler writes were executed. The plugin's allowlist remains the four original reads, so it will not automatically poll these candidates.

Rollback: restore /etc/vcontrold/vito.xml-bak to /etc/vcontrold/vito.xml and reload the daemon's definitions. Do not run rollback now; the additions have been accepted and are awaiting post-repair validation.
