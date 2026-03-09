/**
 * ADL v1 types – frontend only. See ADL_SPEC.md and adl-schema.json.
 */

export const ADL_VERSION = 1

export interface CodeLine {
  text: string
  addr?: string
}

export interface FlagsSnapshot {
  N: number
  Z: number
  C: number
  V: number
}

export interface StepSnapshot {
  pc: string
  lineCounter: number
  activeInstructionIndex?: number
  registers: Record<string, string>
  flags: FlagsSnapshot
  memoryDelta?: Record<string, number>
}

export interface FragmentSpan {
  text: string
  start: number
  end: number
  id?: string
}

export type AnchorRef =
  | { kind: 'CodeLineAddr'; lineIndex: number }
  | { kind: 'PC'; pc: string }
  | { kind: 'RegisterRow'; reg: string }
  | { kind: 'CanvasComponent'; id: 'CU' | 'REG' | 'ALU' }
  | { kind: 'CodeFragment'; lineIndex: number; fragment: string }
  | { kind: 'FloatingToken'; tokenId: string }

export type ADLEvent =
  | { type: 'SetActiveLine'; by: 'pc' | 'index'; value: number | string }
  | { type: 'FocusCanvas'; target: 'CU' | 'REG' | 'ALU' | 'None' }
  | { type: 'MarkRegister'; reg: string; mode: 'read' | 'write' | 'clear' }
  | { type: 'OverlayArrow'; from: AnchorRef; to: AnchorRef; text: string }
  | { type: 'AnnotateBus'; text: string; at: 'aluInputA' | 'aluInputB' | 'writeback' }
  | { type: 'Wait'; ms: number }
  | { type: 'HighlightCodeFragment'; lineIndex: number; fragments: FragmentSpan[] }
  | { type: 'AnimateFragmentMove'; lineIndex: number; fragments: FragmentSpan[]; duration?: number; target?: 'codeBoxCenter' }
  | { type: 'ClearFragmentHighlight' }

export interface TraceStep {
  snapshot: StepSnapshot
  events: ADLEvent[]
}

export interface InitialState {
  registers?: Record<string, string>
  flags?: FlagsSnapshot
  memoryDelta?: Record<string, number>
}

export interface TraceResponse {
  adlVersion: number
  code?: CodeLine[]
  disassembly?: unknown[]
  initialState?: InitialState
  steps: TraceStep[]
}

/** For streaming: same shape as one element of TraceResponse.steps */
export type TraceStepPayload = TraceStep
