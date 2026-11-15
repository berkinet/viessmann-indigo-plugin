# Full KO2B alarm block

Version 0.2.23 adds two String states on the system device: alarmBlock (decoded diagnostic summary) and alarmBlockRaw (29 space-separated hex bytes). Read on the existing fault-check interval, through the single shared communications manager. No fault-display, burner interpretation or write authorization depends on this new diagnostic.

The 29 bytes are not 29 separately understood fields. The decoded summary includes every byte indexed 0..28, plus catalogue-known fields: byte14 low nibble system number, mask20 fault-manager flag, mask10 change flag; byte15 participant; bytes16..17 little-endian year; bytes18..22 month/day/hour/minute/second; byte27 faulty participant; byte28 hexadecimal fault code. Controller timestamp components are shown as heater-local wall time, without inventing a UTC offset. Invalid components are explicitly labelled. Unknown bytes are preserved, not assigned meanings.

Strict 29-byte framing rejects malformed, all-05 and all-FF samples. On a failed fault check the decoded state says Unavailable, rather than presenting an old successful decode as current. The raw state carries the latest reply if available, or is empty when no block reply was obtained. Transport loss marks the decoded state unavailable; a retained raw state outside a completed fault check is historical. A valid transport read does not establish physical correctness or active-fault semantics.

The additive read-only definition in config/209f-alarm-commands.xml was installed on the Pi, with backup revtest.xml.before-alarm29-20261115T124143; production service restarted successfully. Owner installs the plugin release from GitHub. The full block was live-tested during normal zero-output and enabled operation, but not during D1. Captures and detailed experiment report remain in the local ChatGPT workspace reports/status-block-experiments-2026-11-15.

Required daemon fix: receive_nb used a 100-byte logging buffer; its 29-byte hex dump requires 102 bytes including label and terminator. Enlarged to 3*MAXBUF+32 in local and Pi io.c, rebuilt and installed with /usr/local/sbin/vcontrold.before-alarm29 backup. This affects diagnostic logging capacity, not read interpretation.

## Timestamp-independent change trigger — 0.2.27

Use system state **Alarm block contents (excluding time)** (`alarmBlockContent`)
with an **any change** trigger. In that trigger's logging action, log the existing
full `alarmBlock` state. The stable content state contains indexed hexadecimal
bytes for every member except controller clock bytes 16–22. Unknown/undecoded
members are included, as is the controller changeFlag bit itself.

This avoids timestamp-only log events without depending on catching the temporary
changeFlag. A fault code can change while the sampled flag stays false, as seen
when the owner cleared D1 on 15 November. Both fault onset and clear change content.
A first valid sample can trigger once when initializing the new state.

`alarmBlockContentValid` describes the latest attempt. Failed reads retain the
last content and set validity false instead of generating a false alarm-content
change. Full decoded/raw alarm states keep their existing error reporting. The
content and full decoded block are published in the same state-update batch.

This observes differences between samples; a transient that changes and reverts
entirely between reads remains undetectable. The controller's alarmChangeFlag
is retained as a diagnostic state, not recommended as the sole logging trigger.
