/**
 * TracePlayer: interprets ADL steps and events, drives UI via a driver interface.
 * Supports batch (TraceResponse) and async iterator (streaming).
 */

import type {
  ADLEvent,
  AnchorRef,
  FragmentSpan,
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
  /** Highlight code fragments within a line (optional: no-op if not implemented). */
  highlightCodeFragments?(lineIndex: number, fragments: FragmentSpan[]): void
  /** Animate fragments from source to center, scale up; store positions for FloatingToken (optional). */
  animateFragmentMove?(
    lineIndex: number,
    fragments: FragmentSpan[],
    options?: { duration?: number; target?: 'codeBoxCenter' }
  ): Promise<void>
  /** Clear fragment highlights (optional: no-op if not implemented). */
  clearFragmentHighlight?(): void
  /** Called at start of seek/replay to reset fragment UI state (optional). */
  resetFragmentState?(): void
  /** Called before each step to hide overlay arrows / bus annotations (optional). */
  clearStepOverlays?(): void
}

export interface TracePlayerOptions {
  speed?: number
  driver: TracePlayerDriver
}

export interface TraceControllerOptions {
  /**
   * Default playback speed multiplier (only affects Wait events).
   */
  speed?: number
}

export interface TraceController {
  /**
   * Total number of steps in the trace.
   */
  readonly totalSteps: number
  /**
   * Current step index (0-based). -1 means before the first step.
   */
  readonly currentIndex: number

  /**
   * Seek to the given step index.
   * Strategy: apply snapshots for intermediate steps (no events), execute events only for the target step to avoid flicker.
   */
  stepTo(index: number, options?: { animateWaits?: boolean; speed?: number }): Promise<void>

  /**
   * Auto-play forward from the current (or given) index until:
   * - the last step is reached, or
   * - `shouldContinue()` returns false.
   */
  playForward(options: {
    fromIndex?: number
    speed?: number
    animateWaits?: boolean
    shouldContinue: () => boolean
  }): Promise<void>
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

/**
 * Create a timeline controller backed by a TraceResponse.
 *
 * Design notes:
 * - seek (stepTo): applies snapshots for intermediate steps (no events), executes events
 *   only for the target step — eliminates flicker caused by rapid SetActiveLine replays.
 * - auto-play (playForward): incremental, never replays from the start — avoids O(N²) cost and flicker.
 * - When animateWaits=false, Wait events are skipped and AnimateFragmentMove runs at duration=0
 *   (preserving floatingTokenPositions so subsequent FloatingToken OverlayArrows resolve correctly).
 */
export function createTraceController(
  trace: TraceResponse,
  driver: TracePlayerDriver,
  opts: TraceControllerOptions = {}
): TraceController {
  const steps = trace.steps ?? []
  const baseSpeed = opts.speed && opts.speed > 0 ? opts.speed : 1

  let currentIndex = -1

  const totalSteps = steps.length

  function applyInitialState() {
    if (trace.initialState) {
      const initSnapshot: StepSnapshot = {
        pc: '',
        lineCounter: 0,
        registers: trace.initialState.registers || {},
        flags: trace.initialState.flags || { N: 0, Z: 0, C: 0, V: 0 },
        memoryDelta: trace.initialState.memoryDelta,
      }
      driver.applySnapshot(initSnapshot)
    }
  }

  /**
   * Seek to the given index:
   * - Intermediate steps: apply snapshot only, no events (avoids SetActiveLine flicker between lines).
   * - Target step: apply snapshot then execute events; when animateWaits=false, Wait is skipped
   *   and AnimateFragmentMove runs at duration=0.
   */
  async function seekToIndex(
    targetIndex: number,
    options?: { animateWaits?: boolean; speed?: number }
  ): Promise<void> {
    const clampedIndex = Math.max(0, Math.min(totalSteps - 1, targetIndex))
    const effectiveSpeed = options?.speed && options.speed > 0 ? options.speed : baseSpeed
    const animateWaits = options?.animateWaits ?? false

    if (driver.resetFragmentState) {
      driver.resetFragmentState()
    }
    if (driver.clearStepOverlays) {
      driver.clearStepOverlays()
    }
    applyInitialState()

    // Intermediate steps: snapshot only, no events
    for (let i = 0; i < clampedIndex; i++) {
      const step = steps[i]
      if (step) driver.applySnapshot(step.snapshot)
    }

    // Target step: apply snapshot then run events
    const finalStep = steps[clampedIndex]
    if (finalStep) {
      driver.applySnapshot(finalStep.snapshot)
      for (const ev of finalStep.events) {
        if (ev.type === 'Wait' && !animateWaits) continue
        await runEvent(ev, driver, effectiveSpeed, animateWaits)
      }
    }

    currentIndex = clampedIndex
  }

  /**
   * Incremental forward playback: executes only the next step's events without replaying from the start.
   * Avoids O(N²) replay cost and visual reset flicker from resetFragmentState.
   */
  async function playForwardImpl(options: {
    fromIndex?: number
    speed?: number
    animateWaits?: boolean
    shouldContinue: () => boolean
  }): Promise<void> {
    const { fromIndex, speed, animateWaits = true, shouldContinue } = options
    const effectiveSpeed = speed && speed > 0 ? speed : baseSpeed
    const startIndex =
      typeof fromIndex === 'number' && fromIndex >= -1 ? fromIndex : currentIndex

    let idx = startIndex
    while (idx < totalSteps - 1) {
      if (!shouldContinue()) break
      const nextIndex = idx + 1
      const step = steps[nextIndex]
      if (step) {
        // Clear per-step visual state from previous step
        if (driver.resetFragmentState) driver.resetFragmentState()
        if (driver.clearStepOverlays) driver.clearStepOverlays()
        driver.applySnapshot(step.snapshot)
        for (const ev of step.events) {
          if (!shouldContinue()) break
          if (ev.type === 'Wait' && !animateWaits) continue
          await runEvent(ev, driver, effectiveSpeed, animateWaits)
        }
      }
      currentIndex = nextIndex
      idx = nextIndex
      if (!shouldContinue()) break
    }
  }

  return {
    get totalSteps() {
      return totalSteps
    },
    get currentIndex() {
      return currentIndex
    },
    async stepTo(index, options) {
      if (totalSteps === 0) {
        currentIndex = -1
        return
      }
      await seekToIndex(index, options)
    },
    async playForward(options) {
      if (totalSteps === 0) {
        currentIndex = -1
        return
      }
      await playForwardImpl(options)
    },
  }
}

async function runEvent(
  ev: ADLEvent,
  driver: TracePlayerDriver,
  speed: number,
  animateWaits: boolean = true
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
    case 'HighlightCodeFragment':
      if (driver.highlightCodeFragments) {
        driver.highlightCodeFragments(ev.lineIndex, ev.fragments)
      }
      break
    case 'AnimateFragmentMove': {
      // During seek: run at duration=0 to skip animation delay while preserving
      // floatingTokenPositions so subsequent FloatingToken OverlayArrows resolve correctly.
      const scaledDuration = animateWaits ? Math.round((ev.duration ?? 600) / speed) : 0
      if (driver.animateFragmentMove) {
        await driver.animateFragmentMove(ev.lineIndex, ev.fragments, {
          duration: scaledDuration,
          target: ev.target,
        })
      }
      break
    }
    case 'ClearFragmentHighlight':
      if (driver.clearFragmentHighlight) {
        driver.clearFragmentHighlight()
      }
      break
    default:
      break
  }
}
