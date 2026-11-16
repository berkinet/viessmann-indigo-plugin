# Read diagnostics and bounded recovery — 0.2.29

Prompted by the 15–16 November overnight logs: intermittent daemon Wrong result replies, unmapped party responses and connection deadlines.

Full-poll temperature reads and the periodic party-mode/target reads now get at most two attempts. After a failure the client discards its socket and partial buffer, reconnects, verifies clock health and retries the read once. Other independent datapoints can still succeed after a framed data error. A repeated transport failure stops the remaining full-poll reads as before. Initial connection/clock failures continue through the existing health schedule rather than repeating a full batch immediately. Error-history/alarm/production reads keep their existing periodic schedule; holiday sequences and writes are not automatically retried.

Warnings record failed command, attempt, elapsed time, bounded reply text and recovery. Categories distinguish vcontrold-reported ERR replies, communication failures, unmapped UNKNOWN responses and plugin data-validation failures. A validation error is a rejected sample, not proof of a plugin bug: check XML address, length, unit, scale/enumeration and raw evidence before changing a definition. No rejected reply becomes valid data.

A failed full-poll health check is displayed once in lastError as Controller health check, rather than four misleading per-sensor failures. Internal missing-value bookkeeping/validity remains intact. Clock errors identify getSystemTime and the transport deadline includes command and elapsed time.

For invalid party-mode values the client requests getProbePartyModeRaw, a read-only one-byte command at KO2B 2330 without RT conversion. This is a subsequent sample, not guaranteed to be the byte that produced the earlier UNKNOWN. It is diagnostic only and never interpreted as a mode. An old daemon without the command reports that failure rather than preventing bounded recovery.

Pi deployment: tools/production/add_party_raw_command.py verifies or adds the fixed getter, resolves the existing vito.xml symlink, validates XML and creates a dated backup. Installed on 16 November; vcontrol.service restarted and active. No boiler set commands were sent. Existing vcontrold debug logging is left unchanged: Wrong result bytes are rejected within vcontrold and are not supplied in its TCP error reply. Correlate the recorded command/time with daemon logs to investigate those bytes; the plugin does not pretend to have them.

Tests retain existing TCP framing, cancellation, write rejection/readback and lifecycle coverage. Added cases cover one-retry success, exhausted retries, timeout reconnection, cancellation without retry, raw party diagnostics, error-source classification and deduplicated health reporting.

## 0.2.30 — informational optical resync

A failed controller-health exchange with a fresh detected optical activity probe now displays **Resync optical link**, without setting Indigo's device error flag. This applies to health-only system updates and full-poll device updates. Health/reading validity remains false and diagnostic errors remain available; retained values are not revalidated. A successful health exchange restores Online. Detected activity without a failed health exchange retains Pending. Known controller faults retain priority and their error flag; absent TCP or absent optical activity retains the existing failure behavior. Resync describes the recovery path, not a guarantee that recovery will succeed.
