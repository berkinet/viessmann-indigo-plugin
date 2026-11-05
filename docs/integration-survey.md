# vcontrold home automation repository survey

Checked 5 November 2026 using GitHub repository search, primary README/configuration documentation, and selected client implementations. This is a discovery survey and selective source review, not an installation test, full code audit, or evidence that any project's command addresses work on our 209F controller. No third-party code was run, no new integration was installed, and no Pi/plugin configuration changed.

## Most relevant clients and integrations

| Platform / interface | Repository or source | Architecture and value for our project |
| --- | --- | --- |
| Home Assistant | [Alexandre-io/homeassistant-vcontrol](https://github.com/Alexandre-io/homeassistant-vcontrol) | Add-on with vclient/MQTT bridge; supports a remote existing daemon. Configurable command types and refresh interval. Good source for recovery, stale MQTT values and write handling. |
| ioBroker | [misanorot/ioBroker.viessmann](https://github.com/misanorot/ioBroker.viessmann) | Imports command definitions locally or via SSH and maps them to ioBroker objects. Supports selecting different polling rates and forced queries. Useful configurable-capability UI precedent. |
| Home Assistant / MQTT | [b00lduck/vcontrold-homeassistant-mqtt-adapter](https://github.com/b00lduck/vcontrold-homeassistant-mqtt-adapter) | TypeScript service connecting to existing vcontrold TCP, polling configured sensors, and publishing MQTT discovery. Source separates queueing, protocol handling, parsing and MQTT. |
| Generic MQTT | [tma/vcontrold-mqttd](https://github.com/tma/vcontrold-mqttd) | Rust implementation with persistent TCP, serialized access, reconnects, polling and request/response MQTT interface. Closest transport comparison to our manager. Repository also packages a daemon; inspect deployment assumptions rather than assuming every example is a remote-only bridge. |
| FHEM | [89_VCLIENT.pm](https://github.com/fhem/fhem-mirror/blob/main/fhem/FHEM/89_VCLIENT.pm) | Client module for an existing external vcontrold, unlike FHEM's direct-serial VCONTROL variants. Maps commands to readings and permits regular, daily and manual-only queries. |
| Homebridge / HomeKit | [planetk/homebridge-vcontrold](https://github.com/planetk/homebridge-vcontrold) | Configurable temperature sensors, heating/DHW thermostat accessories and switches. Historical design example; selected source has limitations noted below. |
| openHAB | [chriskloe/vMon](https://github.com/chriskloe/vMon) | Java monitoring bridge; related OpenV wiki documents integration with openHAB and the fork's HTTP authentication support. Historical REST/item mapping example. |
| Domoticz | [c4rd0n/domotic](https://github.com/c4rd0n/domotic) | Configuration and Lua scripts for a Vitoladens 300C/Vitotronic 200 installation. Historical appliance-specific examples, not a general maintained adapter. |
| EDOMI | [MrIcemanLE/LBS-vcontrold](https://github.com/MrIcemanLE/LBS-vcontrold) | Logic block using vclient, with JSON I/O and documented request pacing/retry changes. Historical integration example. |
| Generic MQTT write transactions | [antoinevalentinHA/boilerack](https://github.com/antoinevalentinHA/boilerack) | Wraps an existing daemon through vclient subprocesses; emphasizes command expiry, duplicate handling and actual readback. Explicitly not a Home Assistant integration or program-policy layer. Useful future write-path reference. |

Additional smaller/older clients found include [euweb/pyvclient](https://github.com/euweb/pyvclient), [clemens321/vi2mqtt](https://github.com/clemens321/vi2mqtt), [cruwaller/viessmann_optolink2mqtt](https://github.com/cruwaller/viessmann_optolink2mqtt), and [slashx57/HA_vcontrold](https://github.com/slashx57/HA_vcontrold). Search descriptions identify these as MQTT/client integrations, but they received less review than the shortlist above; HA_vcontrold's README supplied almost no documentation.

## Useful findings for our architecture

1. **Persistent TCP is an established approach.** The Rust bridge's [client](https://github.com/tma/vcontrold-mqttd/blob/main/src/vcontrold/client.rs) uses a connection mutex and consumes the vctrld prompt. The TypeScript [client](https://github.com/b00lduck/vcontrold-homeassistant-mqtt-adapter/blob/master/src/vcontrold-client.ts) queues requests and discards a timed-out socket so a late response cannot be assigned to the next request. These support our serialized, prompt-framed, reconnect-on-desynchronization approach. This is not evidence that they implement our explicit Optolink close-between-cycles policy.
2. **MQTT push usually sits downstream of polling.** The reviewed HA add-on, Rust bridge and TypeScript adapter poll vcontrold then publish values. Their MQTT updates are not evidence of unsolicited controller notifications on port 3002. Our present polling requirement stands.
3. **Multiple polling classes are worth considering later.** FHEM's regular/daily/manual selection and ioBroker's per-value intervals would fit slowly changing burner statistics, timers and configuration. We should retain the simple 180-second system property initially, then add slower or demand-only groups when the command set grows. This is a recommendation, not a change implemented by the survey.
4. **Health must include usable data.** The HA add-on documents stale retained readings, publication-based health, bounded command budgets and avoiding automatic replay of ambiguous setter operations. Our timestamps/validity separation is consistent with that concern. A future whole-cycle budget and explicit stale-age policy would be useful refinements.
5. **Keep measurement distinct from target.** The Homebridge [source](https://github.com/planetk/homebridge-vcontrold/blob/master/index.js) uses target temperature as CurrentTemperature when no current command is supplied. Do not adopt that fallback. Its request-per-call transport is also not our shared polling design. Study accessory presentation, not assume production correctness or current Homebridge compatibility.
6. **Verify writes through readback.** Boilerack's documented transaction model is relevant when we implement controls. Its author's production claim is a report about that installation, not verification on our equipment.
7. **Handle character encoding deliberately.** The Rust protocol reader comments specifically discuss non-ASCII units. Our current transport deliberately decodes ASCII and would reject a non-ASCII response; actual deployed unit strings and captures should guide any UTF-8/encoding extension. Do not silently drop undecodable bytes.

## Related replacements, not clients of our daemon

- [yoda-jm/vcontrold-go](https://github.com/yoda-jm/vcontrold-go): direct KW2/Optolink implementation with MQTT/Home Assistant discovery and climate entities. README labels real-hardware verification for 2098 KW2; it does not establish 209F support. Its [KW2 override](https://github.com/yoda-jm/vcontrold-go/blob/main/overrides/vitola200-kw2.xml) reads burner starts at 088A as four bytes, reinforcing that as a test candidate. README reports reserved sensor values including FF/FFFF and FF7F; investigate their applicability on our controller before adding decoding rules. This is a source of failure-mode ideas, not a reason to replace our daemon.
- [speters/vogod](https://github.com/speters/vogod): direct Optolink daemon exposing REST and Bonjour/mDNS, using ecnDataPointType/ecnEventType-style data. README explicitly describes beta quality. Useful broader data-model reference, not a drop-in vcontrold client.

## Activity snapshot and limits

Live GitHub API pushed_at values below were checked rather than relying on search-engine cache or updated_at. A push may involve a non-default branch, documentation, or automation; it is not proof of ongoing support or quality. None of these repositories was marked archived by the checked API response.

| Repository | Last push date reported |
| --- | --- |
| Alexandre-io/homeassistant-vcontrol | 2026-10-16 |
| misanorot/ioBroker.viessmann | 2026-10-21 |
| tma/vcontrold-mqttd | 2026-10-28 |
| b00lduck/vcontrold-homeassistant-mqtt-adapter | 2026-08-05 |
| antoinevalentinHA/boilerack | 2026-09-06 |
| yoda-jm/vcontrold-go | 2026-11-03 |
| speters/vogod | 2026-03-30 |
| chriskloe/vMon | 2022-11-10 |
| planetk/homebridge-vcontrold | 2015-12-01 |
| c4rd0n/domotic | 2015-03-02 |
| MrIcemanLE/LBS-vcontrold | 2018-04-09 |
| slashx57/HA_vcontrold | 2021-10-12 |

Priority for any deeper review: Rust TCP bridge, ioBroker configuration model, FHEM polling classes, then Boilerack's future write path. The survey gives no reason to abandon the agreed direct Indigo integration or add MQTT as a dependency. Code reuse, if later proposed, requires inspecting the applicable file license; no external source code was copied into our plugin.
