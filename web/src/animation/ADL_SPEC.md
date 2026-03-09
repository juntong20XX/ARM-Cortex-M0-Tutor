# ADL v1 – Animation Description Language

Backend-generated trace + animation events; frontend interprets and drives code highlight, registers/flags/memory, canvas focus, and overlay arrows.

- **adlVersion**: `1` (for future extension).
- **Memory**: per-step **delta** only; key = hex address string, value = **byte** (0–255). Frontend maintains full 64KB mirror.

---

## TraceResponse (top-level)

| Field | Type | Description |
|-------|------|-------------|
| `adlVersion` | number | Must be `1` |
| `code` | CodeLine[] | Optional. Source lines with optional address. |
| `disassembly` | array | Optional. Full disassembly window for left panel. |
| `initialState` | InitialState | Optional. Initial registers/flags/memory delta. |
| `steps` | TraceStep[] | Each step: snapshot + events. |

---

## StepSnapshot (per-step state)

| Field | Type | Description |
|-------|------|-------------|
| `pc` | string | e.g. `"0x00000056"` |
| `lineCounter` | number | Line index in source. |
| `activeInstructionIndex` | number | Optional. Index of current instruction in code. |
| `registers` | Record<string, string> | e.g. `{ "r0": "0x0", "r1": "0x255", ... }` |
| `flags` | { N, Z, C, V } | Each `0` or `1`. |
| `memoryDelta` | Record<string, number> | Address (hex string) → **byte** value. |

---

## AnchorRef (stable anchors for overlay/canvas)

| Kind | Payload | Description |
|------|---------|-------------|
| `CodeLineAddr` | `{ kind, lineIndex: number }` | Left-panel code line by index. |
| `PC` | `{ kind, pc: string }` | Resolve to code line by PC. |
| `RegisterRow` | `{ kind, reg: "R0" }` | Right-panel register row. |
| `CanvasComponent` | `{ kind, id: "CU" \| "REG" \| "ALU" }` | Canvas box. |
| `CodeFragment` | `{ kind, lineIndex, fragment: string }` | Specified text fragment within a code line (for highlight/anim start). |
| `FloatingToken` | `{ kind, tokenId: string }` | Token animated to code box center; used as arrow endpoints. |

---

## ADL events (per-step `events[]`)

| type | Payload | Description |
|------|---------|-------------|
| `SetActiveLine` | `by: "pc" \| "index", value` | Set active code line. |
| `FocusCanvas` | `target: "CU" \| "REG" \| "ALU" \| "None"` | Highlight canvas component. |
| `MarkRegister` | `reg, mode: "read" \| "write" \| "clear"` | Mark register row. |
| `OverlayArrow` | `from: AnchorRef, to: AnchorRef, text: string` | Draw arrow with label. `from`/`to` may be `FloatingToken`. |
| `AnnotateBus` | `text, at: "aluInputA" \| "aluInputB" \| "writeback"` | Data flow label on bus. |
| `Wait` | `ms: number` | Optional pause (frontend may use global speed). |
| `HighlightCodeFragment` | `lineIndex`, `fragments: Array<{ text, start, end }>` | Highlight character ranges in code line. |
| `AnimateFragmentMove` | `lineIndex`, `fragments: Array<{ text, start, end, id? }>`, `duration?`, `target?: "codeBoxCenter"` | Animate fragments from source to center, scaling; `id` used for `FloatingToken`. |
| `ClearFragmentHighlight` | (none) | Clear code fragment highlights (optional, may be implicit before next event). |

---

## Example payload (batch TraceResponse)

```json
{
  "adlVersion": 1,
  "code": [
    { "text": "ldr r1, =0x255", "addr": "0x00000054" },
    { "text": "adds r0, r1, #0x5", "addr": "0x00000056" },
    { "text": "MOVS r1, #5", "addr": "0x00000058" }
  ],
  "initialState": {
    "registers": { "r0": "0x0", "r1": "0x0", "r2": "0x0", "r13": "0x200003f0", "r14": "0x51", "r15": "0x54" },
    "flags": { "N": 0, "Z": 1, "C": 0, "V": 0 }
  },
  "steps": [
    {
      "snapshot": {
        "pc": "0x00000056",
        "lineCounter": 1,
        "registers": { "r0": "0x0", "r1": "0x255", "r15": "0x56" },
        "flags": { "N": 0, "Z": 1, "C": 0, "V": 0 }
      },
      "events": [
        { "type": "SetActiveLine", "by": "index", "value": 1 },
        { "type": "FocusCanvas", "target": "CU" },
        { "type": "OverlayArrow", "from": { "kind": "CodeLineAddr", "lineIndex": 1 }, "to": { "kind": "CanvasComponent", "id": "CU" }, "text": "Decode: adds r0, r1, #5" },
        { "type": "MarkRegister", "reg": "R1", "mode": "read" },
        { "type": "OverlayArrow", "from": { "kind": "CodeLineAddr", "lineIndex": 1 }, "to": { "kind": "RegisterRow", "reg": "R1" }, "text": "Read R1 = 0x255" },
        { "type": "Wait", "ms": 800 }
      ]
    },
    {
      "snapshot": {
        "pc": "0x00000058",
        "lineCounter": 2,
        "registers": { "r0": "0x25a", "r1": "0x255", "r15": "0x58" },
        "flags": { "N": 0, "Z": 0, "C": 0, "V": 0 }
      },
      "events": [
        { "type": "SetActiveLine", "by": "index", "value": 2 },
        { "type": "FocusCanvas", "target": "ALU" },
        { "type": "MarkRegister", "reg": "R1", "mode": "clear" },
        { "type": "MarkRegister", "reg": "R0", "mode": "write" },
        { "type": "AnnotateBus", "text": "0x255 + 5 = 0x25a", "at": "writeback" },
        { "type": "OverlayArrow", "from": { "kind": "CanvasComponent", "id": "ALU" }, "to": { "kind": "RegisterRow", "reg": "R0" }, "text": "Write R0 = 0x25a" },
        { "type": "Wait", "ms": 800 }
      ]
    }
  ]
}
```

---

## Example: MOVS operand highlight and move (new events)

For `MOVS r1, #3`, fragments `r1` and `#3` can be highlighted, animated to code box center, then linked by arrow:

```json
{
  "type": "HighlightCodeFragment",
  "lineIndex": 2,
  "fragments": [
    { "text": "r1", "start": 6, "end": 8, "id": "dest" },
    { "text": "#3", "start": 11, "end": 13, "id": "src" }
  ]
},
{
  "type": "Wait",
  "ms": 300
},
{
  "type": "AnimateFragmentMove",
  "lineIndex": 2,
  "fragments": [
    { "text": "r1", "start": 6, "end": 8, "id": "dest" },
    { "text": "#3", "start": 11, "end": 13, "id": "src" }
  ],
  "duration": 600,
  "target": "codeBoxCenter"
},
{
  "type": "OverlayArrow",
  "from": { "kind": "FloatingToken", "tokenId": "src" },
  "to": { "kind": "FloatingToken", "tokenId": "dest" },
  "text": "#3 → R1"
}
```

---

## Streaming (reserved)

Same step shape: each SSE `data:` or WebSocket message can be a single `TraceStep` (with `snapshot` + `events`). Frontend consumes via `AsyncIterable<TraceStep>`.
