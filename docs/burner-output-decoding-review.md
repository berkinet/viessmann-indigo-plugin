# Burner-output definition review — 14 November 2026

User questioned decoding after repeated FF -> 127.5% output. The deployed command requests 55E3, one byte, unit PR. PR is a short with V/2 scaling. Source procGetUnit copies two bytes for short regardless of the one-byte command length. In the observed logs the second byte was zero, yielding integer 255 -> 127.5%. Thus command width and decoder width are inconsistent; changing interpretation must not silently turn FF into a valid percentage. FF may be an unavailable/unsupported value or a different field encoding; this is not established.

Re-examined pinned ViessData21 archive DP_Listen_2.zip at revision 80a2a8cf6e0506edcb93fd39659f044bc88a4c17, file DP_V200KO2B.txt. It lists both nvoPWRState_CFDM_value and nvoPWRState_CFDM_state at A38F, each Byte. These names mean actual installation/output value and status. That is exact-model evidence for investigating a multi-field structure, but the extracted list does not specify field offsets or byte order.

Working reports on other controller families describe A38F as a two-byte read, with first byte output at half-percent scaling and second byte status. These are first-hand observations on other models, not a verified KO2B mapping. Source: https://forum.fhem.de/index.php?topic=20280.1215 (posts 1223–1224). Their 55D3 alternative is a different address from our 55E3; do not conflate them.

Recommended next controlled read-only test: raw A38F/2 on the KO2B, compare both bytes against Vitodata/panel during confirmed on and off states, and inspect wider 55E3 only if independent model evidence justifies it. Do not use a packed value+status as one integer percentage. Retain raw bytes and distinguish unavailable status from zero output. Do not clamp 127.5 or assume FF means 100%.

This review changed no XML, decoder, plugin, heater setting or running connection. The installed plugin retains the invalid-value guard. A new live probe needs serialized access through/released by the persistent optical owner; do not start a competing serial client. Primary model archive: https://github.com/philippoo66/ViessData21/blob/80a2a8cf6e0506edcb93fd39659f044bc88a4c17/DP_Listen_2.zip .

## Offline reinterpretation requested by owner

Owner clarified that the requested experiment was to decode existing captures using the newly found structure information, not to query the heater. No new live query, reload or connection recycle occurred. The briefly staged additive A38F XML definition was restored exactly from its backup before any reload.

Archived raw getBurnerOutput entries examined contain only the single byte FF at 55E3 (61 entries across overlapping log excerpts, not necessarily distinct reads). Candidate numerical interpretations: unsigned byte 255; unsigned half-percent 127.5%; signed byte -1; bit pattern 11111111. The short decoder's second zero byte is buffer padding in the observed trace, not a captured second data byte. None of these interpretations establishes a valid 0–100% output. Signed -1 suggests a possible missing/invalid sentinel, but that meaning is not proven for 55E3.

The exact-model A38F value/status pair concerns another address. No A38F two-byte capture is present in the saved evidence, so its separate fields cannot be recovered by reinterpreting the FF byte from 55E3. No decoder or production mapping was changed. A future live A38F read would be separate work, not a prerequisite for reporting this offline result.

## Owner-requested live A38F read

After the offline result, the owner explicitly requested a current value. Added a temporary getaddr-only A38F/2 command and reloaded daemon metadata. The established Indigo TCP child (not the production daemon) was terminated to release the serial lock for the queued diagnostic. A getSystemTime baseline returned a valid timestamp, then A38F/2 returned C8 01 twice at 09:38:58 and 09:39:00 UTC (10:38:58 and 10:39:00 Paris).

Candidate interpretation: first byte C8=200 at half-percent scaling -> 100%; second byte 01 -> on. This is plausible for a single-stage burner but does not independently establish flame or distinguish requested output from actual firing. Current physical burner/panel state was not independently confirmed for these exact samples. No production output mapping was changed.

The explicit close exchange disconnected without an acknowledgement; socket closure releases that diagnostic session. Finally restored the active XML exactly from its fresh backup and reloaded it. No temporary command remains, no heater setter/reset was issued, and no plugin release was made. Raw transcript: sources/a38f-current-2026-11-14.json.


## Recovery and interpretation follow-up

The owner accepted retaining the candidate C8/2 + status decode, while noting it still does not explain the physical burner state. This acceptance does not establish that status 01 confirms flame. The candidate interpretation and raw capture are retained; no permanent production output mapping was changed during the diagnostic.

Subsequent verification found repeated clients waiting for the serial semaphore without progress. This was an actual communications interruption after the diagnostic, not evidence that the original A38F reply was cached. A supervised native daemon service and bounded log-based watchdog were installed; fresh clock, error, relay and burner replies resumed at 09:47 UTC. See communications-watchdog.md.

Source inspection of parser.c RECV clears the receive buffer before framer_receive; io.c receive_nb reads serial bytes. The framer preset-result path is protocol link-status handling, not an ordinary measurement cache. This makes general measurement caching by vcontrold unlikely. Controller-side retained values, incorrect field semantics and stream/framing problems remain distinct possibilities; fresh serial transport alone does not prove the field reflects current combustion.
