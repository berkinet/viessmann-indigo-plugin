# Vitodata screenshots versus daemon reads — 14 November 2026

Owner supplied state-page screenshot captured at 10:17:39 Paris and error-history screenshot captured at 10:16:56. Screenshots do not show the acquisition time of the operating values; capture time is not necessarily measurement time. These are observations, not instructions or authority to change settings.

## Fault record agreement

Vitodata's two latest D1 records are 14 November 09:47:10 and 05:03:42. These exactly match the decoded getError0 records in the daemon log. Earlier rows also include the 13 November 15:22:46 and 14:30:08 records we captured. This validates the history-record reading/decoding but not active-fault semantics.

Daemon first observed the new records at about 05:15:28 and 09:58:39 Paris. The controller clock is roughly 11 minutes slow relative to host observation time; getSysTime's +0000 suffix is Pi formatting, not proof the controller wall-clock fields are UTC. Owner clarified 05:19, 09:56 and 10:00 were Vitodata email-send times, not physical transition times. Keep event clock, daemon observation and notification times separate.

## State comparison

| Field | Vitodata screenshot | Nearby Optolink reading, Paris observation time |
|---|---|---|
| Boiler water | 56.5 C | 27.3 C, 10:16:04 (also 10:12:50 and 10:19:15) |
| Outside | 12.9 C | 14.5 C, 10:16:06 |
| DHW | 45.3 C | 34.1 C, 10:16:10 |
| Room measurement | 20.8 C | 20.7 C, 10:16:12 |
| Standard room target | 23 C | 23 C, 10:16:08 |
| Burner stage 1 | OFF | 0842=01 at 10:15:58, 10:17:05, 10:18:13 |
| Relay status | Not displayed raw | 82 00 at 10:15:56, 10:17:03, 10:18:11 |
| Burner percentage | Not displayed | FF -> 127.5%, rejected as out of range |

Other supplied reference values: current circuit mode 1 Reduced; selected program 2 Heating+DHW; reduced and party targets 15 C; A1 pump, output 20, burner stage 1, cylinder primary and DHW circulation pumps all off; DHW heating disabled. Flow 56 C, stage-1 run hours 5220.62, starts 84877. These could be useful for future synchronized mode/pump/counter comparisons. A standard target of 23 while the current mode is reduced is not a contradiction: standard and effective/reduced targets are distinct.

## Search for older matching temperatures

Compared 330 logged full-reading snapshots across 13–14 November. The nearest four-field matches were around 00:57–01:04 Paris on 14 November. At 00:57:26–34 the readings were boiler 56.6, outside 13.2, DHW 45.3, room 20.8. At 01:00:36–44 they were 56.4, 12.7, 45.2, 20.8. No exact four-field match was found; sum absolute differences was 0.4 C for the best sets. This is a heuristic comparison, not proof of acquisition time.

The state screenshot resembles an older overnight condition much more closely than contemporaneous raw Optolink temperatures. Cached/cloud-delayed values are therefore a plausible explanation, while different source/filtered datapoints remain possible. Do not use the screenshot as a synchronized ground truth for 0842 without establishing its last-update/acquisition time. The owner's independent physical fault observation still directly challenges interpreting 0842=01 as confirmed flame.

No code, controller settings, clock or XML changed for this comparison. Evidence: sources/viessmann-vitodata-window-20261114.json and sources/viessmann-vitodata-closest-20261114.json. Local image paths are preserved in the conversation; image binaries are not copied into the public project.
