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
   * 默认播放速度倍数（仅影响 Wait 事件）
   */
  speed?: number
}

export interface TraceController {
  /**
   * Trace 总步数
   */
  readonly totalSteps: number
  /**
   * 当前所在的 step 索引（0-based）
   */
  readonly currentIndex: number

  /**
   * 跳转到指定 step 索引。
   * 实现策略：对中间步骤只应用 snapshot（不执行事件），仅对目标步执行事件，避免闪烁。
   */
  stepTo(index: number, options?: { animateWaits?: boolean; speed?: number }): Promise<void>

  /**
   * 从当前（或指定）索引向前自动播放，直到：
   * - 到达最后一步，或
   * - `shouldContinue()` 返回 false。
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
 * 创建一个基于 TraceResponse 的时间轴控制器。
 *
 * 设计要点：
 * - seek (stepTo): 对中间步骤只应用 snapshot（不执行事件），仅对目标步执行事件。
 *   消除了历史 SetActiveLine 等事件快速触发导致的命令行闪烁。
 * - 自动播放 (playForward): 增量式逐步执行，不从头重放，避免 O(N²) 重播和闪烁。
 * - Wait / AnimateFragmentMove 在 animateWaits=false 时均跳过延迟（AnimateFragmentMove
 *   以 duration=0 执行，保留 floatingTokenPositions 状态供后续 OverlayArrow 使用）。
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
   * 跳转到指定 index：
   * - 中间步骤只应用 snapshot，不执行事件，避免 SetActiveLine 等在旧行之间闪烁。
   * - 目标步骤执行事件；animateWaits=false 时跳过 Wait，AnimateFragmentMove 以 duration=0 执行。
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

    // 中间步骤：只应用 snapshot，不执行事件
    for (let i = 0; i < clampedIndex; i++) {
      const step = steps[i]
      if (step) driver.applySnapshot(step.snapshot)
    }

    // 目标步骤：应用 snapshot 并执行事件
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
   * 增量式向前播放：每次只执行下一步的事件，不从头重放。
   * 避免 O(N²) 重播以及 resetFragmentState 引起的视觉清零闪烁。
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
      // seek 时以 duration=0 执行：跳过动画延迟，但保留 floatingTokenPositions
      // 状态，确保后续 OverlayArrow(FloatingToken) 能正确解析坐标。
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
