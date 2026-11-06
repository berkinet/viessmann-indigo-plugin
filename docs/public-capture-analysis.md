# Examination of actual public Optolink captures — 6 November 2026

## Materials actually opened

1. [Optolink Bridge's analyze_trace_example.txt](https://github.com/kristian/optolink-bridge/blob/a35ea8f09edd8f90b0e823d1c8a862eb319878bb/tools/analyze_trace_example.txt), pinned to a35ea8f09edd8f90b0e823d1c8a862eb319878bb. Despite its name, the file contains timestamped directional raw hex traffic, not merely an analysis summary. SHA256 e60ad585f0772bedba5aaf56092fa83e140b021cea484d26e9beef9de71243e6.
2. [USB-Duo/Sniffer public capture workbook](https://www.godemann.de/test/git/Vitoconnect-Output-public.xlsm), linked by the [OpenV hardware documentation](https://github.com/openv/openv/wiki/Bauanleitung-USB_Duo-Sniffer). Opened read-only using the bundled spreadsheet importer; no macros executed and no workbook edits/export performed. SHA256 c9482a59e03980e023b396094378a3fa610240aee831bc7b2d6da6d427888f17. Contains sheets Ruhe, Import2, Import3. Metadata identifies a Vitodens 300 WB3C and captures dated September 2018, not our 209F unit.

No Pi or heater access was performed. [Computed summary](sources/public-capture-summary.json) preserves counts and validation outcomes. Original third-party captures are linked rather than redistributed in the repository.

## Independent packet checks

Parsed P300 frames using their declared length, checked the additive checksum, separated request/response message identifiers, and paired responses by address and the complete function/sequence byte. For the directional text trace, also required the response destination to match the originating client. For workbook sheets, direction is inferred from the message identifier; their imported frame rows omit idle/control-byte traffic and do not provide per-frame timestamps.

| Capture | Request frames | Response frames | Complete pairs | Distinct response addresses | Unmatched responses |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bridge raw example, about 27.4 seconds | 334 | 333 | 333 | 298 | 0 |
| Workbook Ruhe | 310 | 310 | 310 | 56 | 0 |
| Workbook Import2 | 378 | 378 | 378 | 55 | 0 |
| Workbook Import3 | 542 | 542 | 542 | 62 | 0 |

All 667 framed packets in the Bridge example and all 2,460 workbook frames pass length/checksum checks. The Bridge trace ends immediately after a request to 2003; its absent response is an end-of-file boundary, not evidence of a fault. Its initial 04 / 05 / 16 00 00 / 06 sequence is normal session initialization, not an unsolicited data record or malformed frame. No message-ID 2 (UNACKD) data frame appears in these samples.

**Every recorded data response is explained by an earlier request. These captures supply no positive evidence of unsolicited temperature or active-fault broadcasts.** This conclusion is limited to the samples and their retained records; the workbook's frame importer cannot establish what idle bytes it omitted, and the examples do not cover every startup/fault condition or controller model.

## What the bytes actually reveal

### 1. Multi-value reads, not just individual sensor registers

The workbook contains repeated 22-byte reads at 2500 and 3500, 16-byte reads at 080C and 1050, 34-byte reads at 2302/3302, and 48-byte timer reads. These are concrete examples of one requested address yielding multiple fields. A recorder preserving the whole response can reveal information that a single-field decoder discards. Exact field meanings require validation; address names alone are insufficient.

### 2. A mode transition is visible in the capture

Import2 row 94 records a write of 02 to 2323; row 95 is the response. Row 174 requests 22 bytes at 2500, and row 175 returns the block. The workbook notes say the app changed heating circuit 1 from DHW-only to heating plus DHW. This establishes the recorded write/read addresses and association with the observed action, not a universal mode map.

Import3 provides a within-capture comparison: row 378 writes 02 to 2323, and row 622 writes 02 to 3323. The 2500 and 3500 blocks change over that recording. For example, zero-based payload offset 1 changes from 00 to 02 in both blocks; several other bytes also change. Do not infer that all changed bytes are mode fields, or that one can safely copy the write values to 209F.

### 3. Fault history is returned in blocks

The workbook repeatedly reads 54 bytes at 7507 and 36 bytes at 753D. Those lengths correspond to six and four nine-byte records respectively; together they cover ten history slots using only two requests. Their payloads are unchanged across these three captures. This supports more efficient history acquisition and shows how long responses can carry multiple records. It does not establish a current-active-fault bit. The leading code bytes in these WB3C records differ from our captured D1 records, and are not diagnosed here.

### 4. Temperature records have extra bytes

The Bridge sample includes 01CB -> DA 01 40. The first two bytes, little-endian /10, are 47.4 C; the third byte is additional information, whose meaning is not proved by this sample. It also contains 01CA -> 00 00 46 and other status-like suffixes. Such records must not automatically be interpreted as a valid zero-temperature measurement. This is independent raw evidence of the three-byte record issue seen in the WO1C owner discussion.

### 5. Some traffic is RPC rather than a simple sensor read

The Bridge sample includes 32 paired remote-procedure calls to A800 with nine-byte returned records. It also includes long three-byte-per-entry runs in the 9200/9300 ranges and a 42-byte B280 record containing a UTF-16-like heating-circuit label. Those are solicited configuration/structured data, not newly observed broadcasts. This demonstrates why a useful capture tool should retain function codes, parameters and full payloads rather than attempting to parse every reply as a temperature.

### 6. What is NOT in the samples

Neither capture set contains direct reads of our room-temperature candidates 0896, 0898, 0116 or 01D6. Other temperature blocks are present, but their components cannot be labelled measured room temperature from these captures alone.

The 130B compressor-phase example mentioned in the earlier report comes from the Bridge README's separate worked analysis. **130B is not present in the downloadable raw example examined here.** It must not be represented as a finding independently reproduced from this sample. The raw example's identity bytes assemble to 20 4D 01 45 00 00 05 0E, confirming it is a different device family from ours.

## Implication for our recorder proposal

These captures demonstrate useful findings from recording normal operating conversations: compound records, read/write address asymmetry, status transitions and unusual encodings. They do not demonstrate additional autonomous broadcasts. Capturing only our small known polling set will not automatically discover other addresses. A richer diagnostic-client conversation can expose more, provided the recorder captures both directions with one serial owner or a proper hardware tap. Keep unmatched frames as findings for investigation, not automatically as proof of a broadcast, because captures can begin mid-session or lose bytes.

Source cell references for follow-up: Import2!A94:I95 and A174:AD175; Import3 writes at rows 378/379 and 622/623; Ruhe fault blocks at rows 132/133 (7507) and 134/135 (753D). All row numbers refer to the original public workbook.
