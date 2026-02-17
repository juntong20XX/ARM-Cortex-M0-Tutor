/**
 * Streaming hook for ADL trace.
 * Same step shape as TraceResponse.steps[] – use with playTraceStream().
 * Example SSE consumption (when backend supports it):
 *
 *   const es = new EventSource('/api/trace/stream')
 *   const steps = streamTraceStepsFromSSE(es)
 *   await playTraceStream(steps, { driver, speed: 1 })
 */

import type { TraceStep } from './adl-types'

/**
 * Yield TraceStep from EventSource message events.
 * Expects each event.data to be JSON string of { snapshot, events }.
 */
export async function* streamTraceStepsFromSSE(
  eventSource: EventSource
): AsyncGenerator<TraceStep> {
  const queue: TraceStep[] = []
  let resolve: (() => void) | null = null
  const next = () => new Promise<void>(r => { resolve = r })

  eventSource.onmessage = (e: MessageEvent) => {
    try {
      const step = JSON.parse(e.data as string) as TraceStep
      if (step?.snapshot && Array.isArray(step?.events)) queue.push(step)
    } catch (_) { /* ignore */ }
    if (resolve) { resolve(); resolve = null }
  }
  eventSource.onerror = () => {
    if (resolve) { resolve(); resolve = null }
  }

  while (true) {
    while (queue.length) yield queue.shift()!
    await next()
    if (eventSource.readyState === EventSource.CLOSED) break
  }
}
