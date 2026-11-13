# Entire restart-capture transition analysis — 13 November 2026

Snapshot: 30 samples, 15:23:41–15:38:21 Paris. Times below are first observed responses, not exact physical event times; sampling is every 30 seconds. The monitor continues beyond this snapshot.

| First observed (Paris) | Relay response | XOR against previous valid response |
|---|---|---|
| 15:23:55 | 83 80 | — |
| 15:25:55 | 82 80 | 01 00 |
| 15:28:52 | ERR: Error in wait, terminating; Error executing getProbeRelayStatus | — |
| 15:29:16 | 80 20 | 02 A0 |
| 15:32:48 | 82 20 | 02 00 |
| 15:33:53 | 83 20 | 01 00 |
| 15:35:18 | 82 20 | 01 00 |

## Other fields

- Controller identity metadata stayed unchanged in all samples. This is configured daemon metadata, not independent controller telemetry.
- getError0 initially held D1 timestamp 14:30:08 on the controller clock. At 15:33:51 Paris it changed to D1 timestamp 15:22:46, remaining unchanged through the snapshot. No sampled no-error/00 record was seen.
- All controller-clock reads succeeded and advanced; no backward/stalled clock was observed. This does not exclude a restart that preserves the real-time clock.
- One relay command returned a protocol wait error at 15:28:52. Time/history reads in that sample and subsequent samples succeeded. No sample-level socket exception was recorded.
- Complete sample durations ranged from 4.651 to 21.224 seconds, below the 30-second interval.

## Interpretation

First-byte mask 01 is set in 83 xx and clear in 82 xx. It cleared at 15:25:55, set at 15:33:53 alongside a new D1 record, and cleared again at 15:35:18 before the owner’s 15:36 OK SMS. This is the strongest current candidate for a live fault indication. The initial sample already had that bit set, so its onset was not captured.

First-byte mask 02 also changed independently (80 20 -> 82 20 at 15:32:48). The second byte changed 80 -> 20 across the relay-read failure. Those changes cannot be assigned to a fault, burner or pump without additional evidence, and changes across the failed sample are not necessarily simultaneous.

The old error record remained while the candidate fault bit cleared; a later occurrence refreshed its timestamp. Thus error history behaves differently from the live relay state. A brief error-history clearing between samples remains possible. Correlation with the new D1 and the owner’s OK SMS strongly supports investigating mask 01, but no active-fault decoder has been enabled. Nothing published or reset.

## Owner-confirmed running state, later on 13 November

The owner explicitly reported the heater running. Monitor sample 16:34:16 Paris had A152=82 80 while getError0 retained the D1 record timestamp 15:22:46. A following monitor sample returned 05 05; treat this as suspect synchronization contamination, not active-fault evidence. A separate named read at 16:35:34 Paris returned 82 80 and acknowledged optical release.

This supplies a confirmed running-state comparison with first-byte mask 01 clear, versus the earlier new-D1 sample with mask 01 set. It strongly supports this mask as an active-fault candidate for this installation and demonstrates that the retained getError0 D1 is not by itself evidence of a current fault. Any future decoder must reject suspicious synchronization-only responses and avoid interpreting them as bit flags. No decoder change, publication or heater setting change was made for this confirmation.
