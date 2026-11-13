# Persistent communications — 0.2.15

Owner-directed revision on 13 November 2026. Publication approved by the owner on 13 November 2026; Indigo installation remains owner-managed.

## Lifecycle

One manager owns TCP and the optical channel. After daemon identity metadata, getSystemTime is the first optical read. A well-formed eight-byte controller timestamp confirms communication. Healthy polls, health checks, setters and readbacks no longer send close. TCP disconnect on shutdown, endpoint change or uncertain framing releases the daemon's optical ownership. This intentionally retains its serial lock between commands; independent clients may wait for that ownership to be released.

System-device properties:

| Property | Default | Range | Purpose |
|---|---|---|---|
| healthInterval | 30 s | 10–86400 s | Controller-clock check |
| faultInterval | 60 s | 10–86400 s | Error history and raw relay-status sample |
| pollInterval | 180 s | 30–86400 s | Full reading refresh |

Timers are serialized; none run concurrently or generate catch-up bursts. An in-progress command/cycle can delay the next task. Disabled polling disables all periodic work. A manual status request remains a one-shot full poll. Bounded startup retries remain for incomplete initial reading snapshots. A failed clock check disconnects the held session before optional receive-only 05 diagnostics; a healthy session no longer performs that diagnostic before each poll.

The clock's timezone suffix comes from the Pi. Validate timestamp shape/calendar, not agreement with host wall time. A running clock confirms the controller responds even when the burner is stopped with D1; it is not a fault-free signal.

## Writes and display

Live writes remain off by default, limited to standard room/DHW on exact KO2B metadata. They reuse recent clock-health evidence on the same socket (refreshing it when absent/expired), read/check the individual target, send the setter once, require OK and matching readback. No full pre-write snapshot or post-write optical close is required. Ambiguous writes disconnect and are never automatically retried. Setpoint actions still require valid child readings and enabled polling. Pending set confirmation is displayed immediately, across intervening polls, until completion/rejection; last confirmed numeric setpoints remain until readback.

The native heater display now uses verified measured room temperature (0896/2/UT), never the room target. Boiler temperature remains a custom diagnostic. System display gives an established verified fault priority over Online. Unrelated successful clock/data reads cannot clear that fault; only explicit verified-clear evidence can do so. The owner has now authorized a provisional KO2B relay-bit producer; see the trial section below.

## Fault sampling and open mapping

Periodic reads collect getError0 and getProbeRelayStatus. System states retain lastRecordedError, relayStatusRaw, lastFaultCheck and faultCheckError. faultStatus labels the provisional relay interpretation or an unknown sample. Error history alone must not drive an active Error D1 display; a stored record can survive recovery. Read failures retain previous diagnostic strings and expose the sampling error.

The exact-model Vitosoft-derived list names a collective-fault relay field at A152. Live samples were 82 80 earlier and 83 80 during owner-confirmed D1; the earlier state was not confirmed fault-free. No bit assignment has been adopted.

A newly found manufacturer reference, Viessmann LON handbook **5458 766, 11/2010**, describes a cyclic live alarm output that transmits error code 00 when no fault exists. Its SNVT_state table includes collective/burner fault signals. This supports investigating a cleared-state output, but the handbook's model applicability does not explicitly list KO2B and LON wire layout cannot be assumed identical to internal Optolink memory. Source: https://manualzz.com/doc/4363350/viessmann-vitotronic-200--100--050--300-k--333-heizung--v... . Next evidence needed: exact field offsets/masks or a known-clear comparison; no reset or induced fault is authorized by this implementation.

## Verification and test review

Relevant tests were revised for persistent optical ownership instead of per-cycle close. Default-deny writes, bounds, framing/timeout recovery, invalid clock rejection, identity/target checks, ACK/readback uncertainty, startup retry bounds, independent health/status timing, pending-set display, early publication and capability-oscillation regression coverage were retained or added. Historical release-per-cycle assertions were replaced with no-close and clock-recovery checks. All 40 offline tests pass after the owner-authorized relay trial.

Live read-only validation: two forced getSystemTime checks advanced from 14:51:16 to 14:51:19 over the same held-open TCP socket. A separate held-open session read D1 history, A152=83 80, then a full reading snapshot: boiler 51.5 C, outside 18.6 C, standard room target 23 C, DHW 53.7 C, measured room 20.9 C, with no read errors and the same socket retained. No setters/resets or close commands were sent. The test disconnected afterward; production remains on the existing installed release.

Simulator compatibility: unpublished changes in /Users/rdp/Documents/Codex/vcontrold add advancing synthetic time at 088E/8, no-error history at 7507/9 and raw relay zeros at A152/2. Built and black-box tested on the Pi in source-health/build-health without replacing the running service binary or switching production. Existing simulator XML still needs the additive getProbeRelayStatus definition when deploying this draft.

## Owner-authorized relay trial, awaiting publication approval

For exact KO2B/209F metadata (and its marked simulator), read A152 as two raw bytes and interpret mask 01 of the first byte as provisional active fault. Set displays Error plus the latest getError0 code; if history is unreadable or 00, display Error (code unavailable). Clear removes the active fault display while preserving stored error details. Malformed, failed or synchronization-only 05 05 responses do not establish or clear a fault. Unrelated successful time/full-data checks retain the established fault until a valid relay sample changes it. Changes affect only diagnostic/system display states, not setpoint authorization or heater operation. No reset commands are introduced.

The bit is observationally supported on this installation, not certified for every KO2B. Tests cover D1 -> clear with history retained, bad relay retaining the last interpretation, history failure with a set bit, model restriction and unchanged child controls/readings. Forty tests passed. Owner reviewed the consolidated changes and approved push/release.

Final one-shot decoder live check: getSystemTime returned a framed receive/framer error. The result remained active_fault_known=false; no relay-based interpretation was applied and no setter was sent. Result saved in sources/relay-trial-check-2026-11-13.json. This does not supersede the earlier successful persistent-session tests or captured known-running/known-D1 observations.

## System lastSuccess on clock communication

Owner clarified that a successful clock read should advance the system device lastSuccess. It now uses the UTC receipt timestamp from the actual successful clock read, even if Error D1 remains displayed or the full measurement snapshot is incomplete. Cached clock evidence cannot move the timestamp backward. Failed checks do not advance it. Full-snapshot dataValid and child success timestamps are unchanged. All 41 offline tests passed; local 0.2.15 installer rebuilt, still awaiting owner publication approval.
