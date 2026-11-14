# Fault recurrence versus burner signal — 14 November 2026

Owner reported the first error around 05:19 Paris, clearing around 09:56, and recurrence around 10:00. Installed plugin is 0.2.16. Examined daemon logs read-only, using host UTC timestamps converted to Paris rather than the slow controller clock. No extra optical session, reset or setter was issued.

| Paris observation | Event in daemon log |
|---|---|
| 05:05:06–05:11:56 | 0842 stage-1 output was 00; retained previous-day D1 history |
| 05:13:03 | 0842 changed to 01; A152 was 82 20 |
| 05:15:28–30 | New D1 record (controller timestamp 05:03:42); A152 changed to 83 20 |
| 09:55:17 | A152 changed from 83 00 to 82 00; old D1 record retained |
| 09:58:39–41 | New D1 record (controller timestamp 09:47:10); A152 changed to 83 00 |
| 10:00:57 | A152 returned to 82 00; D1 history retained |
| Through 10:12:34, last captured burner read | 0842 still 01 despite owner-reported stopped burner |

Forty-seven captured stage-1 reads were 01 across the sampled post-start windows (05:13 through 10:12); there was no sampled return to 00. Fifty-three captured burner-output reads were raw FF, decoded by the existing XML as 127.5%; the plugin rejects that out-of-range value. One history read at 09:54:25 returned nine 05 bytes and is unusable.

Conclusion: the heating icon is not simply stale. The daemon continues returning 01 while the owner reports the burner stopped. The 0842 signal must therefore be described as stage-1 output/enable, not verified actual firing/flame. Its provisional use as an active-heating icon is contradicted by this observation. Percentage output is currently unusable. The low A152 bit correlates with new error records and reset, but returns clear soon after recurrence; a latched currently-failed interpretation is also not established. Error history timestamps refreshed on recurrence; retained history still cannot independently establish a currently active fault.

These findings challenge both provisional display assumptions. No replacement signal, reinterpretation or plugin update was silently applied. The recorded code is D1 (owner initially typed DS1). Evidence is saved in sources/fault-windows-2026-11-14.json. Exact notification/physical observation times can differ from first daemon observations by minutes; owner times were approximate.
