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

## Versioned XML layout

The owner subsequently authorized moving the complete current command file to `/etc/vcontrold/xml/revtest.xml` and selecting it through the relative symlink `/etc/vcontrold/vito.xml -> xml/revtest.xml`. The move preserves the original file ownership and permissions. Its contents and SHA-256 remain unchanged from the probe deployment recorded above. `/etc/vcontrold/vito.xml-bak` remains untouched as a regular backup file.

The daemon accepted a reload through the symlink. Both that session and a fresh TCP session listed all nine probe commands, confirming the parent daemon also uses the reloaded definitions. Verification used metadata commands only; no heater read/write was sent.

Future targets in the xml directory must be complete vito XML configurations, not the repository fragment. Validate a new target before selecting it; switch the symlink via a prepared temporary link and rename, then reload and verify the catalogue. A link switch alone does not update daemon memory. If a reload fails, restore the previous link and reload it rather than assuming the running configuration changed.

For rollback to the pre-probe content, first copy the unchanged vito.xml-bak into xml under a distinct baseline name, preserving it as a backup, then point vito.xml to that complete baseline and reload. Avoid copying over the live symlink: ordinary copy operations may overwrite its selected target and destroy the intended version history.
