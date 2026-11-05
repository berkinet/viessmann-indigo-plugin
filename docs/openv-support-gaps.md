# OpenV support-gap comparison — 5 November 2026

## Result and scope

Compared the deployed command definitions for selected device 209F with the KO1B/KO2B column of OpenV's address table. Seven documented candidate addresses are absent from the effective configuration. Two existing counter definitions also differ. These are research findings, not validated capabilities of this physical heater. Nothing was changed on the Pi, no daemon reload/restart occurred, and no controller commands were sent.

This comparison concerns what vcontrold can potentially expose, not just the four reads implemented in the Indigo plugin. Existing declarations are not proof that commands work. As requested, unsupported extras were not audited or pruned.

## Which XML is live?

The running process is `/usr/local/sbin/vcontrold`, with no command-line overrides. The installed Linux source defaults to `/etc/vcontrold/vcontrold.xml`. That file selects device 209F and includes `vito.xml` through a relative XInclude, resolving to `/etc/vcontrold/vito.xml`. Thus the owner's proposed path is the configured live command-definition file. This is startup/configuration evidence, not a direct dump of the process's parsed in-memory tree.

Deployed vito.xml SHA-256: `5a93e5ac7f52a308a75451fcdfd679b4383379fc12cb06449301eac80eaf7886`.

There are 149 declarations. Applying 209F child overrides leaves 135 addressed declarations: 92 getaddr reads and 43 setaddr writes (including duplicate command names). Counts are catalogue entries, not unique supported functions. In particular, the getStorageTemp override changes the base 0812/2/UT to 0070/1/UT1, so the base address must not be counted as available.

## Missing candidates from the model-specific column

All addresses below come from the KO1B/KO2B column, not adjacent controller columns. Community entries require validation after repair.

| Function | Candidate address / bytes | Current effective XML | Priority |
| --- | --- | --- | --- |
| A1 flow temperature | 0810 / 2 | No addressed command; getTempVListM1 lacks an address | High: useful heating measurement |
| Filtered DHW/storage temperature | 0812 / 2 | getStorageTemp instead resolves to 0070 / 1 for 209F | Medium: additional filtered reading, not a replacement for getWaterTemp at 0804 |
| Burner stage 1 state | 0842 / 1 | getBrennerStatus reads 551E instead | High: alternative stage-state read; do not assume these are interchangeable |
| Operating-program access | 2323 / 1 | Reads and writes currently target 2301 | High: wiki reports 2301 not writable and 2323 read/write; confirm exact semantics and codes before any write |
| Heating-curve shift | 27D4 / 1 | get/setNiveauM1 uses 2304 | Medium: missing alternative register |
| Heating-curve slope | 27D3 / 1 | get/setNeigungM1 uses 2305 | Medium: missing alternative register; wiki specifies division by 10 |
| Daily solar yield | CF30 / 4 | No command | Conditional: relevant only if solar hardware is installed |

Source: [OpenV address table](https://github.com/openv/openv/wiki/Adressen), KO1B/KO2B column. Do not automatically change addresses of existing commands: retain distinct experimental read names until their meanings are verified.

## Existing definitions that may hide information

- **Burner starts:** getBurnerStarts at 088A reads 2 bytes locally; the model-specific wiki entry says 4. A two-byte result cannot represent the website screenshot's 84269 as a straightforward unsigned count. That supports prioritizing a four-byte comparison, but does not prove the site's reading and raw register are identical.
- **Oil consumption:** getOilUsage at 7574 reads 4 bytes with CO identity conversion. The wiki specifies division by 1000. Capture raw units before presenting litres. Do not globally change CO: other counters use it too, and some appliances may lack a configured consumption calculation.
- **Program decoding:** deployed BA is a shared legacy enumeration (00 Warm-Water, 01 Reduced, 02 Normal, 03/04 Heating and Warm-Water, 05 Shut down). Do not reuse it blindly for 2323 or equate its codes with Vitodata's displayed codes. The five iOS choices remain unmapped.
- **DHW target ambiguity:** the wiki puts both 5502 and 6300 into one boiler-target row with two-byte formatting. Locally 5502 is a two-byte boiler target, while 6300 is a one-byte DHW target. This inconsistent table entry is not evidence to alter the existing DHW length. Keep that question open.

## Measured room temperature and other weaker leads

The KO1B/KO2B table cell for measured room temperature is blank. Blank means undocumented there, not proven unavailable.

[openHab integration](https://github.com/openv/openv/wiki/openHab-Integration) labels its linked example as KO1B, but [the actual example XML](https://raw.githubusercontent.com/wiki/openv/openv/files/vito.xml) selects device **20CB**, not **209F**. That contradiction prevents treating its extra commands as confirmed KO2B support. It nevertheless supplies bounded research candidates missing from our effective XML:

| Candidate function | Example address / bytes | Evidence limit |
| --- | --- | --- |
| Measured/filtered room temperature | 0896 / 2 | Cross-model lead; compare against room sensor display after repair |
| Holiday active | 2535 / 1 | Cross-model lead; interpretation needs its own conversion definition |
| Holiday departure / return | 2309 and 2311 / 8 each | Cross-model lead; date encoding and invalid/unset values unverified |
| Changeover-valve state | 0A10 / 1 | Cross-model lead; physical applicability unverified |

Other differing internal-pump/flame addresses in that example were not promoted to model-specific gaps. Do not replace the live XML with it. It also uses conversion units absent from the deployed setup; addresses alone do not provide usable decoding.

## Already declared, though not yet exposed by our plugin

The current XML already has reads for DHW target, reduced room target, heating flow target, heating/charging/circulation pumps, burner hours, fault history, weekly heating/DHW/circulation timers, economy/party status and targets. Those are plugin-expansion opportunities, not missing XML definitions. Applicability, conversions and native Indigo behavior still require validation.

## Next validation order after repair

1. Verify existing four reads and identify the actual controller including extended hardware/software identity where possible.
2. Add separately named **read-only** candidates for burner stage, A1 flow, filtered storage temperature, and four-byte burner starts. Compare raw/decoded responses with the controller or Vitodata and retain evidence.
3. Investigate 0896 as measured room temperature without assuming it works on 209F.
4. Read and compare 2301/2323 plus heating-curve alternatives. Resolve enumeration and scaling before designing any write experiment.
5. Consider holiday and solar functions only when relevant hardware/features and reliable evidence are available.

No configuration patch or plugin capability was enabled by this report. Writes remain disabled.

## Provenance

Wiki checkout revision: `3a5fee2b0c2060dd38b44a1e173ab8147b29bb8a`. Sources read: Adressen.md, Geräte.md, vito.xml.md, openHab-Integration.md, and files/vito.xml. The devices page associates both KO1B and KO2B with 209F and describes revision-dependent identification: [OpenV devices](https://github.com/openv/openv/wiki/Ger%C3%A4te).

Local comparison applied base command fields then 209F-specific overrides, comparing normalized addresses and lengths rather than command names. The deployed main configuration's unit definitions were read to check CO, CS, BA, UN, UT and UT1 conversions. A local temporary snapshot was used; raw Pi configuration was not added to the public repository.

## Subsequent authorized configuration change

The owner subsequently authorized additions to the deployed XML. See read-probes.md for the nine isolated experimental reads, verification and backup. Their registration does not change the evidence status above or enable them in the plugin.
