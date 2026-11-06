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

## Owner consolidated saved versions

The owner moved saved XML versions into `/etc/vcontrold/xml`. Read-only verification found `revtest.xml`, `vito.xml-1`, `vito.xml-2053`, `vito.xml-bak`, and `vito.xml.sav` there. The current pre-probe backup path is therefore **/etc/vcontrold/xml/vito.xml-bak**, superseding earlier rollback path references. The active symlink still resolves to xml/revtest.xml, its SHA-256 is unchanged, and the selected XML parses successfully. No daemon reload was needed or performed for moving inactive saved versions.

## Separate daemon configuration directory

At the owner's request, daemon configurations were moved to `/etc/vcontrold/daemon-config/`: active `vcontrold.xml`, plus inactive `vcontrol.20cF`, `vcontrold.alt`, and `vcontrold.xml.sav`. `/etc/vcontrold/vcontrold.xml` now points to `daemon-config/vcontrold.xml`. These are separate from the command-definition versions in xml/.

To preserve relative XInclude resolution without editing any XML, `daemon-config/vito.xml` points to `../vito.xml`, which still selects `xml/revtest.xml`. All moved file hashes, ownership and permissions were preserved. The inactive malformed vcontrold.alt was archived as-is, not selected or repaired. The service startup script remains in place.

Metadata-only reload and a fresh-session command-catalogue check passed after relocation; all nine probes remained registered. No heater reads or writes were sent.

## Archived inactive research/test artifacts

At the owner's request, addr1, addr2, code-check.out, command-list, and test-results were moved into /etc/vcontrold/archive/research/; test-xml.sh was moved into archive/scripts/. File contents, ownership and permission bits were verified unchanged. Both active symlinks and their selected configuration hashes were unchanged. No scripts were executed and no service reload was needed or performed.

The /etc/vcontrold top level now contains only archive/, daemon-config/, xml/, and the active vito.xml and vcontrold.xml symlinks. Historical successful read output is preserved in archive/research/test-results for later investigation; it is not current telemetry.

## Fault-status probe — 6 November 2026

At the owner's request, queried the live endpoint with getStatusStoerung (XML address 7579, length 1, unit RT). The response was `ERR: read timeout`, followed by `Error in wait, terminating` and `Error executing getStatusStoerung`. A subsequent independent comparison read getBoilerTemp succeeded with 62.400002 C. Both sessions released Optolink with close. No writes were issued.

RT is defined as enum bytes 00 -> text 0, 01 -> text 1, otherwise UNKNOWN. Those conversions alone do not establish fault polarity or prove this address is supported by this controller. This observation is a command failure while a normal temperature read works; it is not a returned boiler fault indication and must not be treated as either fault-free or fault-active. Leave the candidate outside required polling until address/applicability is investigated. Fault-history reads remain untested.

## Fault probes with heater running — 6 November 2026

The owner confirmed the heater was running and requested another check. Separate read-only sessions returned UNKNOWN for each of getStatusStoerung, getError0, and getError9. Each returned the daemon prompt normally and close confirmed release of the physical serial path. No writes or XML changes were made. Unlike the earlier timeout, these are undecoded responses; they do not establish active-fault polarity, absence of faults, or valid history records. A vcontrold prompt/UNKNOWN alone is not proof that a controller register was decoded successfully. Existing verified temperature reads remain the plugin's evidence for Online. Investigate raw response bytes and conversion/address applicability before adding fault-state behavior. The owner has not installed 0.2.6 and authorizes updating that release rather than incrementing for further pending implementation changes.

## Immediate capture after owner-reported failure — 6 November 2026, 15:57 CET

Repeated getStatusStoerung/getError0/getError9 and comparison getBoilerTemp. All fault queries again displayed UNKNOWN; temperature succeeded at 54.299999 C. Existing daemon debug logging proves real bytes were returned and exposes a conversion gap:

| Query | Earlier running-state capture (14:56 UTC) | Failure capture (14:57 UTC) |
| --- | --- | --- |
| getStatusStoerung | FF | FF |
| getError0 | D1 20 26 11 06 05 15 45 02 | D1 20 26 11 06 05 15 46 28 |
| getError9 | D1 20 26 04 13 01 15 31 20 | D1 20 26 11 01 07 05 16 44 |

Thus UNKNOWN here is not absence of controller communication: vcontrold receives bytes then converts them to UNKNOWN. History content changed, while status byte FF did not distinguish the two captures. The apparent D1 code and following date/time-shaped bytes require model-specific decoding verification; do not claim an active-fault meaning or date format yet. No XML changes or writes were issued. Preserve raw codes even when descriptions are unavailable in future fault decoding work.

## ES decoder restored — 6 November 2026

Owner authorized restoring the saved ES unit. Replaced only that unit in /etc/vcontrold/daemon-config/vcontrold.xml with the ErrorState errstate block from vcontrold.xml.sav, including D1 -> Burner Fault. Original backup: /etc/vcontrold/daemon-config/vcontrold.xml.before-es-fix-20261106T150624Z. Live XML links and register definitions are unchanged; no boiler writes issued. Restart initially encountered a socket bind failure while an old client TCP session was closing; live service subsequently restarted and listened on port 3002.

Post-restart getError0, getError9, getStatusStoerung and comparison getBoilerTemp all returned read timeout. Thus no live decoded history result was obtained during this check, and the failure was not limited to the new fault conversion. Do not claim the decoder has been live-verified or infer physical fault state from these timeouts. General fault status RT remains unchanged.

## Successful live decoder verification — 6 November 2026

On the owner's next retry request, getBoilerTemp returned 52.099998 C; getError0 decoded as `2026-11-06T15:59:43+0000 Burner Fault (D1)`; getError9 decoded as `2026-11-05T09:10:53+0000 Burner Fault (D1)`. These timestamps are vcontrold's verbatim output; their timezone accuracy versus controller local time has not been verified. getStatusStoerung still returned UNKNOWN. The restored ES history conversion is now live-verified for D1. History alone does not establish whether the burner is currently locked out. All sessions were read-only and released the optical link.

## Subsequent failure capture — 6 November 2026, 15:13 UTC

At the owner's report of another failure, queried getStatusStoerung, getError0, getError1, getError9, getBoilerTemp, getOutsideTemp, getWaterTemp and getBrennerStatus. Every read returned ERR: read timeout / Error in wait, terminating. Existing debug logs show the serial path opens, vcontrold sends synchronization byte 04, then times out waiting for 05 before sending the register request. Thus this capture did not reach register-specific data retrieval; trying additional addresses cannot bypass the missing synchronization response. The TCP daemon still returned prompts/errors normally. This differs from earlier failed-burner captures that returned temperature and D1 history records; do not conflate burner lockout with loss of optical communication, or infer a specific physical cause. No configuration changes, service restarts, or controller writes were issued.
