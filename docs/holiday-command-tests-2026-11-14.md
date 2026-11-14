# KO2B holiday get/set tests — 14 November 2026

Owner authorized holiday getter/setter testing and supplied departure/return dates, finally 20 November–13 December 2026. Production polling was briefly stopped for each exclusive loopback diagnostic daemon on port 3004, and restored in finally blocks. No competing optical clients were used.

## Commands and observations

- getHolidayStart / setHolidayStart: 2309, eight bytes, TI conversion.
- getHolidayEnd / setHolidayEnd: 2311, eight bytes, TI conversion.
- Raw getter aliases: getProbeHolidayStartRaw and getProbeHolidayEndRaw.
- getProbeHolidayActiveRaw: 2535, one byte. Exact KO2B catalog HK_FerienbetriebA1M1 specifies one-bit field at MSB-first bit position 7, therefore mask 0x01. Other bits must not be treated as holiday flags.

Initially both dates were 1970-01-01, raw `19 70 01 01 04 00 00 00`, matching the catalog default and owner's previous Vitodata screenshot of disabled holiday dates. Status raw `02`: holiday bit clear.

A raw unit-off no-op departure setter failed locally before serial transmission because the compiled BYTES token expected length one. No retry of that payload was attempted. Standard TI conversion then succeeded for both setters with positive ACK and decoded readback. Initial owner dates were 21 November / 13 December; the owner then supplied 20 November as departure, and that revision was applied and verified twice.

Final state left on the heater:

- Departure: 20 November 2026, raw `20 26 11 20 05 00 00 00`.
- Return: 13 December 2026, raw `20 26 12 13 07 00 00 00`.
- Holiday status: `02` on both final checks; holiday-active bit clear.

The controller normalizes Sunday to 07 although the generic vcontrold encoder emits weekday zero for Sunday. A strict expected-raw comparison caught that difference; the decoded return date matched, and no uncertain setter was retried. Treat weekday zero/seven deliberately when decoding.

The Pi runs UTC. TI setter conversion adjusts its input into daemon local time; diagnostic ISO arguments used +0000 so the intended heater-local calendar components were encoded unchanged. The emitted +0000 on getter strings describes the daemon conversion, not proof that holiday scheduling uses UTC. Do not blindly convert these controller-local calendar dates as UTC instants.

## Required three-state distinction

1. No program: both unset sentinel dates and holiday flag clear (observed).
2. Dates stored, not active: valid holiday dates and flag clear (observed for the requested future period). May be future or expired; distinguish those using heater-local calendar dates.
3. Active holiday: holiday-active bit set. Exact KO2B metadata supports this mapping, but an active-period sample has not yet been observed in this test. Do not infer active from the whole 2535 byte being nonzero; 02 is already nonzero while inactive.

Invalid, incomplete, failed or contradictory reads require Unknown rather than falsely assigning one of the above. The KO2B user manual says departure/return are travel dates: holiday operation begins at midnight AFTER departure and ends at midnight ON return. Thus the stored test dates imply 21 November 00:00 through 13 December 00:00 at the heater, subject to installation behavior.

## Sources

- Exact KO2B extracted catalog: local DPDefinitions.xml, version 0.0.26.4683, model row 340. Date events FerienBeginnA1M1 (306), FerienEndeA1M1 (309) declare DateBCD, eight bytes and Virtual_WRITE. Full prior local extraction: /tmp/viessmann-ko2b-catalog.json.
- Owner-published example get/set XML using the same date addresses, lengths and TI unit: https://malura.de/en/blog/automatic-export-of-my-viessmann-heating-system
- First-hand future/active discussion (cross-model): https://forum.fhem.de/index.php?topic=67744.120
- KO2B user manual, pages 26–27: https://cdn0.scrvt.com/2828ebc457efab95be01dd36047e3b52/36c9022e1850de54/e2e41d426f46/Operating-Instructions-Vitotronic-200-Control.PDF

Deployed XML backup: /etc/vcontrold/xml/revtest.xml.before-holiday-20261114T150434. Detailed captures on Pi: /tmp/viessmann-holiday-20261114T150434.json and subsequent viessmann-holiday-set/date/final captures. The added commands remain available in production; no Indigo holiday action or polling has been added yet.
