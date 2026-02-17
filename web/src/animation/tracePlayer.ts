/**
 * TracePlayer: interprets ADL steps and events, drives UI via a driver interface.
 * Supports batch (TraceResponse) and async iterator (streaming).
 */

import type {
  ADLEvent,
  AnchorRef,
  StepSnapshot,
  TraceResponse,
  TraceStep,
} from './adl-types'

export interface TracePlayerDriver {
  applySnapshot(snapshot: StepSnapshot): void
  setActiveLine(index: number): void
  setCanvasFocus(target: 'CU' | 'REG' | 'ALU' | 'None'): void
  markRegister(reg: string, mode: 'read' | 'write' | 'clear'): void
  setOverlay(from: AnchorRef, to: AnchorRef, text: string): void
  wait(ms: number): Promise<void>
}

export interface TracePlayerOptions {
  speed?: number
  driver: TracePlayerDriver
}

/**
 * Play a batch trace (TraceResponse). Returns after all steps.
 */
export async function playTrace(
  trace: TraceResponse,
  options: TracePlayerOptions
): Promise<void> {
  const { driver, speed = 1 } = options
  for (const step of trace.steps) {
    driver.applySnapshot(step.snapshot)
    for (const ev of step.events) {
      await runEvent(ev, driver, speed)
    }
  }
}

/**
 * Play from an async iterator of steps (for SSE/WebSocket streaming).
 * Same step shape as TraceResponse.steps[]. Consumes until iterator done.
 */
export async function playTraceStream(
  steps: AsyncIterable<TraceStep>,
  options: TracePlayerOptions
): Promise<void> {
  const { driver, speed = 1 } = options
  for await (const step of steps) {
    driver.applySnapshot(step.snapshot)
    for (const ev of step.events) {
      await runEvent(ev, driver, speed)
    }
  }
}

async function runEvent(
  ev: ADLEvent,
  driver: TracePlayerDriver,
  speed: number
): Promise<void> {
  switch (ev.type) {
    case 'SetActiveLine':
      driver.setActiveLine(
        typeof ev.value === 'number' ? ev.value : parseInt(String(ev.value), 10) || 0
      )
      break
    case 'FocusCanvas':
      driver.setCanvasFocus(ev.target)
      break
    case 'MarkRegister':
      driver.markRegister(ev.reg, ev.mode)
      break
    case 'OverlayArrow':
      driver.setOverlay(ev.from, ev.to, ev.text)
      break
    case 'AnnotateBus':
      // Optional: driver can implement bus labels; no-op if not supported
      break
    case 'Wait':
      await driver.wait(Math.round(ev.ms / speed))
      break
    default:
      break
  }
}
