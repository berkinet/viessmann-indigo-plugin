# Read-only restart/fault-clear capture

Started on the Pi at the owner's request on 13 November 2026. Captures daemon identity, getSystemTime, getError0 and getProbeRelayStatus every 30 seconds (start-to-start when responses complete in time). The goal is to observe whether error history clears and which relay bits change across a naturally occurring boiler restart/fault recovery. No setter, reset or power command is included.

- Script: `/home/rdp/viessmann/monitor-restart.py`
- Output: `/home/rdp/viessmann/restart-monitor.jsonl`
- Process diagnostics: `/home/rdp/viessmann/restart-monitor.stderr`
- Transient system service: `viessmann-restart-monitor.service`, running as rdp
- Project source: `tools/diagnostics/monitor_restart.py`

The monitor uses port 3002 locally and explicitly releases optical ownership after each sample, then disconnects TCP. It is a temporary diagnostic client and relies on vcontrold's serial lock alongside Indigo. Timeout is 20 seconds per operation; partial responses and failures are logged, with no overlapping/catch-up requests. Each successful response has its own UTC observation timestamp. The controller clock is also retained verbatim; its timezone suffix is host formatting. `changed` excludes routine clock advancement and marks changes to the other sampled responses. It does not itself infer or announce a restart or a cleared fault.

The supervised service continues across boiler restarts but is transient and does not survive a reboot of the Pi. No Codex notification/automation was created. The monitor runs until stopped. Commands on the Pi:

```zsh
sudo systemctl status viessmann-restart-monitor --no-pager
tail -f /home/rdp/viessmann/restart-monitor.jsonl
sudo systemctl stop viessmann-restart-monitor
```

First complete sample: 14:23:41–14:23:55 UTC, duration 13.574 seconds, clock 15:12:57+0000, getError0 `2026-11-13T14:30:08+0000 Burner Fault (D1)`, relay `83 80`; optical release acknowledged. An initial one-shot using a shorter 12-second timeout had timed out on error-history acquisition, so the running monitor uses 20 seconds.

Source and documentation are saved locally under the owner's publication hold; no push/release or plugin installation.

## Brief start and repeated failure reported by owner

Inspected a 15-sample snapshot ending 14:30:50 UTC (15:30:50 Paris). UTC observation timestamps, not the slow controller clock, establish the sequence. All sampled getError0 responses retained the identical D1 record with controller timestamp 14:30:08. Clock reads continued to advance throughout. Relay transitions observed (Paris local time):

| Observation | A152 response |
|---|---|
| 15:23:55 initial | 83 80 |
| 15:25:55 | 82 80 |
| 15:28:52 | ERR: Error in wait, terminating |
| 15:29:16 onward, through the snapshot | 80 20 |

The first change flips bit 0 of the first byte (XOR 01 00). The next successful change flips XOR 02 A0. These are raw transitions, not proven fault semantics. The single relay-read error did not prevent successful time/history reads in that same sample or the following samples.

The owner's report establishes that a short start/failure occurred during monitoring, but exact event times were requested to align the relay values with physical observations. getError0 did not remain cleared in any sample; a brief clearing between 30-second samples remains possible, and the capture does not establish history-ring ordering or repeated-error insertion behavior. Thus it is insufficient as a standalone active/cleared fault indicator on present evidence. Preserve history/status distinction. The monitor remains running; no write, reset, interval change or publication was performed. Raw snapshot: sources/restart-capture-2026-11-13.jsonl.

## New D1 record and subsequent relay reversal

At 15:33:53 Paris, getError0 changed from the old D1 timestamp 14:30:08 to a new D1 timestamp 15:22:46 on the slow controller clock. A152 changed from 82 20 to 83 20 at the same observation. The owner then reported D1 occurring. Subsequent samples through 15:34:48 retained that record and 83 20. At 15:35:18 the relay returned to 82 20 while getError0 still held D1 timestamp 15:22:46. Controller time continued advancing.

The paired new error record and 0->1 first-byte low-bit change is a useful correlation, but its reversal while the owner reports D1 means the bit must **not yet** be implemented as a latched current-fault flag. It may be a changing output or transient indication; no meaning is asserted. No second newer error record had appeared by 15:35:18. The monitor continues and all changes remain unpublished.

## Sequence around the owner's 15:36 OK SMS

By 15:37:18 Paris, 28 samples were available. Relay status was 83 20 at 15:33:53, 15:34:26 and 15:34:48, then 82 20 at 15:35:18, 15:35:51, 15:36:23, 15:36:56 and 15:37:18. getError0 retained the newer D1 record timestamp 15:22:46 throughout those samples. The controller clock advanced normally. The owner supplied an SMS reading `2026-11-13 15:36 OK Casa Milagro heating viessmann.errorcode.SMS.V200K... (D1)`, and reported no fault on the controller display. Its OK wording may denote recovery; notification semantics remain unverified.

This sequence supports the candidate interpretation that A152 first-byte mask 01 is a live/transient fault indication, while getError0 is retained history. It is not yet conclusive: the precise bit mapping and SMS convention still need confirmation. No plugin decoder, service or sampling interval changed; nothing published.

## Capture stopped for 0.2.15 publication

After owner publication approval, stopped viessmann-restart-monitor.service and archived its final capture in sources/restart-capture-2026-11-13.jsonl. This prevents a temporary diagnostic client waiting on the optical lock retained by the updated plugin. The script and Pi log remain available; do not run a second continuous client while the plugin owns the link unless deliberately releasing that ownership.
