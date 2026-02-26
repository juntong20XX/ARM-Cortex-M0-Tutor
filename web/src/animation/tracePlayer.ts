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
   * 实现策略：从初始状态起顺序重放到目标 step，以支持任意前/后退。
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
 * - 支持任意 step 前/后跳转：通过从“初始 UI 状态”开始顺序重放到目标 step 实现。
 * - Wait 事件在 seek 时通常应跳过（animateWaits=false），在自动播放时根据 speed 缩放。
 * - 不直接修改现有 playTrace / playTraceStream，对外保持兼容。
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

  /**
   * 从头重放到指定 index（包含 index）。
   */
  async function seekToIndex(
    targetIndex: number,
    options?: { animateWaits?: boolean; speed?: number }
  ): Promise<void> {
    const clampedIndex = Math.max(0, Math.min(totalSteps - 1, targetIndex))
    const effectiveSpeed = options?.speed && options.speed > 0 ? options.speed : baseSpeed
    const animateWaits = options?.animateWaits ?? false

    // 应用 initialState 快照（如果有）
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

    // 从第 0 步顺序执行到目标步
    for (let i = 0; i <= clampedIndex; i++) {
      const step = steps[i]
      if (!step) continue
      driver.applySnapshot(step.snapshot)
      for (const ev of step.events) {
        if (ev.type === 'Wait' && !animateWaits) {
          continue
        }
        await runEvent(ev, driver, effectiveSpeed)
      }
    }

    currentIndex = clampedIndex
  }

  async function playForwardImpl(options: {
    fromIndex?: number
    speed?: number
    animateWaits?: boolean
    shouldContinue: () => boolean
  }): Promise<void> {
    const { fromIndex, speed, animateWaits, shouldContinue } = options
    const effectiveSpeed = speed && speed > 0 ? speed : baseSpeed
    const startIndex =
      typeof fromIndex === 'number' && fromIndex >= -1 ? fromIndex : currentIndex

    let idx = startIndex
    while (idx < totalSteps - 1) {
      if (!shouldContinue()) break
      const nextIndex = idx + 1
      await seekToIndex(nextIndex, { animateWaits: animateWaits ?? true, speed: effectiveSpeed })
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
