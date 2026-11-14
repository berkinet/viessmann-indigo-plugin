# Pi-side communications recovery

Installed 14 November 2026 after the temporary A38F diagnostic left subsequent clients repeatedly waiting for vcontrold's serial semaphore. The plugin already discards timed-out TCP sessions; reconnecting cannot repair a daemon-side semaphore problem. The recovery does not reset the heater, clear faults, or issue a heater write.

`tools/production/vcontrol.service` replaces the generated SysV wrapper with a native systemd forking service, an explicit `/run/vcontrold.pid`, process-group cleanup, and restart on unexpected process exit. Start failures are bounded to five attempts per ten minutes. The old wrapper could report active/exited without a running daemon; a native service now tracks the actual parent PID. The exact reason the legacy restart failed was not established.

`viessmann-watchdog.timer` runs `watchdog.py` every 30 seconds on the Pi. It observes the existing daemon log, without opening a second optical connection. Repeated recent lock requests with neither a lock acquisition nor serial send/receive progress for 120 seconds trigger `systemctl restart vcontrol.service`. Further watchdog restarts are limited to one per ten minutes. A stopped service stays stopped. Ordinary optical read timeouts, including a powered-off heater, count as serial progress and do not alone trigger recovery. No clients/no requests means no lock-stall restart.

Progress state is stored atomically in `/var/lib/viessmann-watchdog/state.json`. Reboots, log rotation/truncation, or more than 1 MiB of unseen log data invalidate stall evidence and start a new baseline. Detection depends on the present debug log messages; it does not claim to detect every possible daemon hang. Journal entries record recovery actions.

Inspect on the Pi:

```zsh
systemctl status vcontrol.service viessmann-watchdog.timer
journalctl -u viessmann-watchdog.service --since today
```

Installation paths: `/etc/systemd/system/` for the three units; `/usr/local/lib/viessmann/watchdog.py` for the observer. Keep these files from tools/production together. Changing simulator/production setup still requires deliberately selecting the correct service; disable the watchdog timer during unusual diagnostic sessions where lock waiting is intentional.

Verification covers two-minute detection, ongoing owner activity, normal optical timeouts, inactive clients, intentional stop, persisted cooldown and a single restart across successive invocations. Deployment verification checks native MainPID, listener and timer execution. No artificial live heater outage or setter was used for testing.
