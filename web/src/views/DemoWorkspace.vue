<template>
  <div class="demo-container" ref="demoContainerRef" :style="{ paddingLeft: paddingLeft + 'px', paddingRight: paddingRight + 'px' }">
    <!-- 左边缘拖拽条：与内容左边界对齐 -->
    <div class="resize-edge resize-edge-left" :style="{ left: paddingLeft + 'px' }" @mousedown.prevent="startEdgeResize('left', $event)"></div>

    <div class="left-panel" ref="leftPanelRef">
      <div class="toolbar">
        <el-button type="primary" size="small" @click="runDemo" :disabled="isAnimating">
          <el-icon><VideoPlay /></el-icon> Run
        </el-button>
        <el-button
          v-if="projectUuid && allowSave"
          type="success"
          size="small"
          :disabled="saving || isAnimating"
          @click="saveProjectSource"
        >
          {{ saving ? 'Saving...' : 'Save' }}
        </el-button>
        <div class="playback-controls">
          <el-button-group size="small">
            <el-button
              @click="stepBackward"
              :disabled="!traceController || totalSteps <= 0 || currentStepIndex <= 0 || isAnimating"
            >
              ⏮
            </el-button>
            <el-button
              v-if="!isPlaying"
              type="primary"
              @click="playFromCurrent"
              :disabled="!traceController || totalSteps <= 0 || isAnimating"
            >
              ▶
            </el-button>
            <el-button
              v-else
              type="warning"
              @click="pausePlayback"
              :disabled="!traceController || totalSteps <= 0"
            >
              ⏸
            </el-button>
            <el-button
              @click="stepForward"
              :disabled="!traceController || totalSteps <= 0 || currentStepIndex >= totalSteps - 1 || isAnimating"
            >
              ⏭
            </el-button>
            <el-button
              @click="resetPlayback"
              :disabled="!traceController || totalSteps <= 0 || isAnimating"
            >
              ⏹
            </el-button>
          </el-button-group>
          <div class="speed-control" v-if="traceController && totalSteps > 0">
            <span class="speed-label">Speed</span>
            <el-slider
              v-model="playSpeed"
              :min="0.25"
              :max="2"
              :step="0.25"
              :show-tooltip="true"
              class="speed-slider"
            />
            <span class="speed-value">{{ playSpeed.toFixed(2) }}x</span>
          </div>
          <div class="step-summary" v-if="traceController && totalSteps > 0">
            <span class="step-counter">
              Step {{ currentStepIndex >= 0 ? currentStepIndex + 1 : 0 }} / {{ totalSteps }}
            </span>
          </div>
        </div>
        <el-tag v-if="currentStepText" type="warning" class="step-info">{{ currentStepText }}</el-tag>
        <el-tag
          v-if="showAddressUnavailable"
          type="info"
          size="small"
          class="addr-hint"
        >
          地址暂时不可用
        </el-tag>
      </div>
      <div class="editor-wrapper" ref="editorWrapperRef" :style="{ height: editorHeight + 'px' }">
        <div class="code-lines" ref="codeLinesRef">
          <div
            v-for="(line, index) in codeLines"
            :key="index"
            :ref="el => setLineRef(el, index)"
            class="code-line"
            :class="{ 'active-line': index === activeLineIndex }"
          >
            <span class="line-number">{{ index + 1 }}</span>
            <label class="line-content">
              <template v-for="(seg, si) in getLineSegments(line, index)" :key="si">
                <span v-if="seg.highlight" class="fragment-highlight" :data-fragment-id="seg.id">{{ seg.text }}</span>
                <span v-else>{{ seg.text }}</span>
              </template>
            </label>
            <span class="line-addr">{{ codeLineAddresses[index] }}</span>
          </div>
        </div>
      </div>
      <div class="resize-handle-h" @mousedown.prevent="startVertResize('editor-canvas', $event)"></div>
      <div class="canvas-container">
         <div class="canvas-header">
           <span>MCU Architecture & Data Bus</span>
           <div class="canvas-zoom-controls">
             <el-button-group size="small">
               <el-button @click="mcuZoomOut" :disabled="mcuZoom <= 0.5">−</el-button>
               <el-button disabled class="zoom-label">{{ Math.round(mcuZoom * 100) }}%</el-button>
               <el-button @click="mcuZoomIn" :disabled="mcuZoom >= 3">+</el-button>
               <el-button @click="mcuZoomReset">Reset</el-button>
             </el-button-group>
           </div>
         </div>
         <div
           class="canvas-zoom-wrapper"
           ref="mcuZoomWrapperRef"
           @wheel.prevent="onMcuCanvasWheel"
         >
           <div
             class="canvas-zoom-inner"
             :style="{ width: 800 * mcuZoom + 'px', height: 450 * mcuZoom + 'px' }"
           >
             <div
               class="canvas-zoom-content"
               :style="{ transform: `scale(${mcuZoom})` }"
             >
               <canvas ref="archCanvas" width="800" height="450"></canvas>
             </div>
           </div>
         </div>
      </div>
    </div>

    <!-- 可拖拽分隔条 -->
    <div class="resize-handle" @mousedown="startResize"></div>

    <div class="right-panel" ref="rightPanelRef" :style="{ width: rightPanelWidth + 'px' }">
      <!-- Flags Section -->
      <div class="panel-section" :style="{ height: flagsHeight + 'px' }">
        <el-card class="box-card full-card">
          <template #header>
            <div class="card-header"><span>Flags</span></div>
          </template>
          <div class="flags-container">
            <div class="flag-item" :class="{ active: flags.N }">
              <span class="flag-name">N</span>
              <span class="flag-val">{{ flags.N ? 1 : 0 }}</span>
            </div>
            <div class="flag-item" :class="{ active: flags.Z }">
              <span class="flag-name">Z</span>
              <span class="flag-val">{{ flags.Z ? 1 : 0 }}</span>
            </div>
            <div class="flag-item" :class="{ active: flags.C }">
              <span class="flag-name">C</span>
              <span class="flag-val">{{ flags.C ? 1 : 0 }}</span>
            </div>
            <div class="flag-item" :class="{ active: flags.V }">
              <span class="flag-name">V</span>
              <span class="flag-val">{{ flags.V ? 1 : 0 }}</span>
            </div>
          </div>
        </el-card>
      </div>

      <div class="resize-handle-h" @mousedown.prevent="startVertResize('flags-registers', $event)"></div>

      <!-- Registers Section (flex:1, fills remaining) -->
      <div class="panel-section section-flex">
        <el-card class="box-card full-card">
          <template #header>
            <div class="card-header">
              <span>Registers</span>
            </div>
          </template>
          <div class="registers-grid">
            <div
              v-for="reg in registers"
              :key="reg.name"
              class="register-cell"
              :class="{ 'row-read': reg.status === 'read', 'row-write': reg.status === 'write' }"
              @click="toggleRegisterBase(reg.name)"
            >
              <div class="register-name-wrapper">
                <div class="register-name" :id="'reg-row-' + reg.name">
                  {{ reg.name }}
                  <el-icon v-if="reg.status === 'read'" class="status-icon read"><View /></el-icon>
                  <el-icon v-if="reg.status === 'write'" class="status-icon write"><Edit /></el-icon>
                </div>
                <div class="value-base-bars">
                  <span
                    class="base-bar base-bar-dec"
                    :class="{ active: reg.base === 'dec' }"
                  ></span>
                  <span
                    class="base-bar base-bar-hex"
                    :class="{ active: reg.base === 'hex' }"
                  ></span>
                  <span
                    class="base-bar base-bar-bin"
                    :class="{ active: reg.base === 'bin' }"
                  ></span>
                </div>
              </div>
              <div class="register-value-wrapper">
                <span :class="['value-display', reg.status]">
                  {{ formatRegisterValue(reg) }}
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <div class="resize-handle-h" @mousedown.prevent="startVertResize('registers-memory', $event)"></div>

      <!-- Memory Section -->
      <div class="panel-section" :style="{ height: memoryHeight + 'px' }">
        <el-card class="box-card full-card">
          <template #header>
            <div class="card-header">
              <span>Memory</span>
              <div class="memory-range-controls">
                <span class="range-label">Start:</span>
                <el-input
                  v-model="memoryViewStartHex"
                  size="small"
                  class="memory-addr-input"
                  placeholder="0x0000"
                  maxlength="6"
                  @blur="applyMemoryViewStart"
                  @keyup.enter="applyMemoryViewStart"
                />
                <span class="range-label">Count:</span>
                <el-select v-model="memoryViewCount" size="small" class="memory-count-select">
                  <el-option label="8" :value="8" />
                  <el-option label="16" :value="16" />
                  <el-option label="32" :value="32" />
                </el-select>
              </div>
            </div>
          </template>
          <div class="memory-grid">
            <div v-for="item in displayedMemory" :key="item.addr" class="memory-cell">
              <span class="addr">0x{{ item.addr.toString(16).padStart(4, '0') }}:</span>
              <span class="val">{{ item.value }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 右边缘拖拽条：与内容右边界对齐 -->
    <div class="resize-edge resize-edge-right" :style="{ right: paddingRight + 'px' }" @mousedown.prevent="startEdgeResize('right', $event)"></div>

    <!-- Overlay Layer for Arrows (Moved to Container Level) -->
    <svg v-if="demoOverlay.show" class="overlay-svg">
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
        refX="10" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#F56C6C" />
        </marker>
      </defs>
      <path :d="arrowPath" stroke="#F56C6C" stroke-width="3" fill="none" marker-end="url(#arrowhead)" stroke-dasharray="10 5" class="animated-path"/>
      <g class="arrow-label">
        <rect :x="arrowLabelRect.x" :y="arrowTextPos.y - 10" :width="arrowLabelRect.width" height="20" rx="4" fill="rgba(30,30,30,0.92)" stroke="#F56C6C" stroke-width="1"/>
        <text :x="arrowTextPos.x" :y="arrowTextPos.y" fill="#F56C6C" font-weight="bold" text-anchor="middle" dominant-baseline="middle" font-size="12">{{ demoOverlay.text }}</text>
      </g>
    </svg>

    <!-- Floating tokens (after AnimateFragmentMove) -->
    <div class="floating-tokens-layer">
      <div
        v-for="tk in floatingTokens"
        :key="tk.id"
        class="floating-token"
        :class="{ 'floating-token-animating': tk.animating }"
        :data-token-id="tk.id"
        :style="{
          left: tk.x + 'px',
          top: tk.y + 'px',
          transform: `translate(-50%, -50%) scale(${tk.scale})`,
          transition: tk.animating ? `all ${tk.duration}ms ease-out` : 'none'
        }"
      >
        {{ tk.text }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { VideoPlay, View, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { createTraceController, type TraceController } from '@/animation/tracePlayer'
import { ADL_VERSION } from '@/animation/adl-types'
import type { TraceResponse, StepSnapshot, AnchorRef, CodeLine, FragmentSpan } from '@/animation/adl-types'

const props = withDefaults(
  defineProps<{
    initialCode?: string
    projectUuid?: string
    allowSave?: boolean
    initialTrace?: TraceResponse | null
  }>(),
  { initialCode: undefined, projectUuid: undefined, allowSave: true, initialTrace: null }
)

const defaultCode =
  'ldr r1, =0x255\n' +
  'adds r0, r1, #0x5\n' +
  'MOVS r1, #5'
const code = ref(props.initialCode ?? defaultCode)

// 执行得到的代码行（带真实地址），仅在项目模式中使用；Demo 模式仍保持原有行为。
const executionCodeLines = ref<CodeLine[] | null>(null)

watch(
  () => props.initialCode,
  (v) => {
    if (v != null && v !== undefined) code.value = v
  }
)

watch(
  () => props.initialTrace,
  (trace) => {
    if (trace && Array.isArray(trace.code) && trace.code.length > 0) {
      executionCodeLines.value = trace.code
    } else {
      executionCodeLines.value = null
    }
  },
  { immediate: true }
)

const saving = ref(false)
const saveError = ref('')
const lastSavedAt = ref<string | null>(null)

async function saveProjectSource() {
  if (!props.projectUuid) {
    ElMessage.warning('No project linked; cannot save.')
    return
  }
  saving.value = true
  saveError.value = ''
  try {
    const res = await fetch(
      '/api/project/source/' + encodeURIComponent(props.projectUuid),
      {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ source: code.value }),
      }
    )
    const data = await res.json().catch(() => ({}))
    if (res.ok && (data as { success?: boolean }).success !== false) {
      lastSavedAt.value = new Date().toISOString()
      ElMessage.success('Project source saved.')
    } else {
      const msg = (data as { detail?: string }).detail || (data as { msg?: string }).msg || `Save failed (${res.status})`
      ElMessage.error(msg)
      saveError.value = msg
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Network error'
    ElMessage.error(msg)
    saveError.value = msg
  } finally {
    saving.value = false
  }
}

const codeLines = computed(() => {
  return code.value.split('\n')
})

// 地址列显示逻辑：
// - Demo 模式（无 projectUuid）：使用旧逻辑，根据行号顺序生成示例地址；
// - 项目模式（有 projectUuid）：
//   - 若 executionCodeLines 有值：按源码中的有效指令行与 executionCodeLines 逐行对齐，使用 TraceResponse.code.addr；
//   - 否则：地址全部为空，并在 UI 中提示“地址暂时不可用”。
const CODE_BASE = 0x0000

function isExecutableSourceLine(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed) return false
  if (trimmed.startsWith(';')) return false
  if (trimmed.startsWith('//')) return false
  return true
}

const codeLineAddresses = computed(() => {
  const lines = codeLines.value

  // Demo 模式：保持原有示例地址逻辑
  if (!props.projectUuid) {
    const addrs: string[] = []
    let addr = CODE_BASE
    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim()
      if (trimmed) {
        addrs[i] = '0x' + addr.toString(16).padStart(4, '0').toUpperCase()
        addr += 2
      } else {
        addrs[i] = ''
      }
    }
    return addrs
  }

  // 项目模式：优先根据 executionCodeLines 中的真实地址进行映射
  const execLines = executionCodeLines.value
  const addrs: string[] = new Array(lines.length).fill('')

  if (!execLines || execLines.length === 0) {
    // 无执行结果：地址为空，UI 会提示“地址暂时不可用”
    return addrs
  }

  let j = 0
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (!isExecutableSourceLine(line)) {
      addrs[i] = ''
      continue
    }
    const exec = execLines[j]
    if (exec && typeof exec.addr === 'string' && exec.addr) {
      addrs[i] = exec.addr
    } else {
      addrs[i] = ''
    }
    if (j < execLines.length) {
      j += 1
    }
  }

  return addrs
})

const hasExecutionAddresses = computed(() => {
  return !!(props.projectUuid && executionCodeLines.value && executionCodeLines.value.length > 0)
})

const showAddressUnavailable = computed(() => {
  return !!(props.projectUuid && !hasExecutionAddresses.value)
})

// 当前高亮行索引（0-based），对应 "ADD 2 r0 r1" 所在行
const activeLineIndex = ref(3)

// 存储每行 DOM 元素的引用
const lineRefs = ref({})
const setLineRef = (el, index) => {
  if (el) {
    lineRefs.value[index] = el
  }
}
const editorWrapperRef = ref<HTMLElement | null>(null)
const codeLinesRef = ref<HTMLElement | null>(null)

// ADL fragment highlight & float state
interface FragmentHighlightSpan { start: number; end: number; id?: string }
const fragmentHighlights = ref<Map<number, FragmentHighlightSpan[]>>(new Map())
const floatingTokenPositions = ref<Map<string, { x: number; y: number }>>(new Map())
interface FloatingTokenItem { id: string; text: string; x: number; y: number; scale: number; animating: boolean; duration?: number }
const floatingTokens = ref<FloatingTokenItem[]>([])

function getLineSegments(line: string, lineIndex: number): Array<{ text: string; highlight: boolean; id?: string }> {
  const text = line || '\u00A0'
  const spans = fragmentHighlights.value.get(lineIndex)
  if (!spans || spans.length === 0) {
    return [{ text, highlight: false }]
  }
  const sorted = [...spans].sort((a, b) => a.start - b.start)
  const out: Array<{ text: string; highlight: boolean; id?: string }> = []
  let pos = 0
  for (const s of sorted) {
    const start = Math.max(pos, s.start)
    const end = Math.min(s.end, text.length)
    if (start < end) {
      if (start > pos) out.push({ text: text.slice(pos, start), highlight: false })
      out.push({ text: text.slice(start, end), highlight: true, id: s.id })
      pos = end
    }
  }
  if (pos < text.length) out.push({ text: text.slice(pos), highlight: false })
  return out
}

type RegisterDisplayBase = 'dec' | 'hex' | 'bin'

interface RegisterRow {
  name: string
  value: number
  status: '' | 'read' | 'write'
  base: RegisterDisplayBase
}

const registers = ref<RegisterRow[]>(
  Array.from({ length: 16 }, (_, i) => ({
    name: `R${i}`,
    value: 0,
    status: '',
    base: i >= 13 ? 'hex' : 'dec'
  }))
)

// Flags state
const flags = ref({
  N: false, // Negative
  Z: false, // Zero
  C: false, // Carry
  V: false  // Overflow
})

// 内存：64KB 后备存储，视图可指定起始地址与显示条数
const MEMORY_SIZE = 0x10000
const memoryStore = ref(Array(MEMORY_SIZE).fill(0))
const memoryViewStart = ref(0)
const memoryViewCount = ref(16)
const memoryViewStartHex = ref('0x0000')

function applyMemoryViewStart() {
  const s = memoryViewStartHex.value.trim().toLowerCase()
  const hex = s.startsWith('0x') ? s.slice(2) : s
  if (!/^[0-9a-f]+$/.test(hex)) return
  const num = parseInt(hex, 16)
  if (isNaN(num)) return
  const clamped = Math.max(0, Math.min(MEMORY_SIZE - 1, num))
  memoryViewStart.value = clamped
  memoryViewStartHex.value = '0x' + clamped.toString(16).padStart(4, '0').toUpperCase()
}

const displayedMemory = computed(() => {
  const start = memoryViewStart.value
  const count = memoryViewCount.value
  const end = Math.min(start + count, MEMORY_SIZE)
  const list = []
  for (let addr = start; addr < end; addr++) {
    list.push({ addr, value: memoryStore.value[addr] })
  }
  return list
})

// 同步 memoryViewStart 变化到 hex 输入框（外部修改 start 时）
watch(memoryViewStart, (v) => {
  memoryViewStartHex.value = '0x' + v.toString(16).padStart(4, '0').toUpperCase()
}, { immediate: true })
const isAnimating = ref(false)
const currentStepText = ref('')
const currentTrace = ref<TraceResponse | null>(null)
const traceController = ref<TraceController | null>(null)
const currentStepIndex = ref(-1)
const totalSteps = ref(0)
const isPlaying = ref(false)
const isPaused = ref(false)
const playSpeed = ref(1)
const archCanvas = ref<HTMLCanvasElement | null>(null)
const mcuZoomWrapperRef = ref<HTMLElement | null>(null)
const MCU_ZOOM_MIN = 0.5
const MCU_ZOOM_MAX = 3
const MCU_ZOOM_STEP = 0.25
const mcuZoom = ref(1)
const mcuZoomIn = () => { if (mcuZoom.value < MCU_ZOOM_MAX) mcuZoom.value = Math.min(MCU_ZOOM_MAX, mcuZoom.value + MCU_ZOOM_STEP) }
const mcuZoomOut = () => { if (mcuZoom.value > MCU_ZOOM_MIN) mcuZoom.value = Math.max(MCU_ZOOM_MIN, mcuZoom.value - MCU_ZOOM_STEP) }
const mcuZoomReset = () => { mcuZoom.value = 1 }
const onMcuCanvasWheel = (e: WheelEvent) => {
  if (e.deltaY < 0) mcuZoomIn()
  else if (e.deltaY > 0) mcuZoomOut()
}
const leftPanelRef = ref<HTMLElement | null>(null)
const rightPanelRef = ref<HTMLElement | null>(null)
const demoContainerRef = ref<HTMLElement | null>(null)

// ====== 拖拽调整面板尺寸 ======
const rightPanelWidth = ref(350)
const paddingLeft = ref(12)
const paddingRight = ref(12)

// 左面板：编辑器与画布初始比例 3:2，首次加载时按左面板高度计算
const EDITOR_CANVAS_RATIO = [3, 2]
const editorHeight = ref(180)
// 右面板：Flags / Registers / Memory 默认比例 1:3:2，首次加载时按右面板高度计算
const FLAGS_REGISTERS_MEMORY_RATIO = [1, 3, 2]
const RESIZE_HANDLE_H = 6
const flagsHeight = ref(110)
const memoryHeight = ref(200)

// 通用拖拽状态
let dragCtx: {
  type: 'col' | 'editor-canvas' | 'flags-registers' | 'registers-memory' | 'edge-left' | 'edge-right'
  startX?: number
  startY?: number
  startValue: number
} | null = null

const lockDrag = (cursor: string) => {
  document.body.style.userSelect = 'none'
  document.body.style.cursor = cursor
}

const unlockDrag = () => {
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

// --- 水平拖拽（左右面板） ---
const startResize = (e: MouseEvent) => {
  dragCtx = { type: 'col', startX: e.clientX, startValue: rightPanelWidth.value }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  lockDrag('col-resize')
}

// --- 垂直拖拽（上下组件） ---
const startVertResize = (type: 'editor-canvas' | 'flags-registers' | 'registers-memory', e: MouseEvent) => {
  let startValue = 0
  if (type === 'editor-canvas') startValue = editorHeight.value
  else if (type === 'flags-registers') startValue = flagsHeight.value
  else if (type === 'registers-memory') startValue = memoryHeight.value

  dragCtx = { type, startY: e.clientY, startValue }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  lockDrag('row-resize')
}

// --- 边缘拖拽（左右边距） ---
const startEdgeResize = (side: 'left' | 'right', e: MouseEvent) => {
  dragCtx = {
    type: side === 'left' ? 'edge-left' : 'edge-right',
    startX: e.clientX,
    startValue: side === 'left' ? paddingLeft.value : paddingRight.value
  }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  lockDrag('col-resize')
}

// --- 统一拖拽处理 ---
const onDrag = (e: MouseEvent) => {
  if (!dragCtx) return

  if (dragCtx.type === 'edge-left') {
    // 左边缘：向右拖增大 padding
    const dx = e.clientX - (dragCtx.startX ?? 0)
    paddingLeft.value = Math.max(0, Math.min(300, dragCtx.startValue + dx))
  } else if (dragCtx.type === 'edge-right') {
    // 右边缘：向左拖增大 padding
    const dx = e.clientX - (dragCtx.startX ?? 0)
    paddingRight.value = Math.max(0, Math.min(300, dragCtx.startValue - dx))
  } else if (dragCtx.type === 'col') {
    // 水平：调整右面板宽度
    if (!demoContainerRef.value) return
    const containerRect = demoContainerRef.value.getBoundingClientRect()
    const newWidth = containerRect.right - e.clientX - paddingRight.value
    rightPanelWidth.value = Math.max(180, Math.min(containerRect.width * 0.6, newWidth))
  } else {
    // 垂直：调整组件高度
    const dy = e.clientY - (dragCtx.startY ?? 0)
    if (dragCtx.type === 'editor-canvas') {
      editorHeight.value = Math.max(60, dragCtx.startValue + dy)
    } else if (dragCtx.type === 'flags-registers') {
      flagsHeight.value = Math.max(60, dragCtx.startValue + dy)
    } else if (dragCtx.type === 'registers-memory') {
      // 向下拖 → memory 变小
      memoryHeight.value = Math.max(60, dragCtx.startValue - dy)
    }
  }
}

const stopDrag = () => {
  dragCtx = null
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  unlockDrag()
}

const demoOverlay = ref({
  show: false,
  from: { x: 0, y: 0 },
  to: { x: 0, y: 0 },
  text: ''
})

const arrowPath = computed(() => {
  const { from, to } = demoOverlay.value
  // Create a curved path
  const dx = to.x - from.x
  const dy = to.y - from.y
  const controlX = from.x + dx * 0.5
  const controlY = from.y + dy * 0.1
  return `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`
})

// Arrow text position: offset perpendicular to avoid overlapping tokens
const arrowTextPos = computed(() => {
  const { from, to } = demoOverlay.value
  const midX = (from.x + to.x) / 2
  const midY = (from.y + to.y) / 2
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.sqrt(dx * dx + dy * dy) || 1
  const perpX = -dy / len
  const perpY = dx / len
  const offset = 22
  return {
    x: midX + perpX * offset,
    y: midY + perpY * offset
  }
})

const arrowLabelRect = computed(() => {
  const w = Math.max(80, demoOverlay.value.text.length * 7)
  return { width: w, x: arrowTextPos.value.x - w / 2 }
})

// Architecture Layout Constants (Scaled Up)
const LAYOUT = {
  CU: { x: 60, y: 150, w: 140, h: 120 },
  REG: { x: 350, y: 50, w: 260, h: 80 },
  ALU: { x: 480, y: 280, size: 80 }
} as const

// Resolve ADL AnchorRef to container-relative { x, y } for overlay
function resolveAnchor(anchor: AnchorRef): { x: number; y: number } | null {
  const containerEl = demoContainerRef.value
  if (!containerEl) return null
  const containerRect = containerEl.getBoundingClientRect()

  if (anchor.kind === 'CodeLineAddr') {
    const lineEl = (lineRefs.value as any)[anchor.lineIndex]
    if (!lineEl) return null
    const addrEl = lineEl.querySelector('.line-addr') as HTMLElement | null
    if (!addrEl) return null
    const r = addrEl.getBoundingClientRect()
    return {
      x: r.left - containerRect.left,
      y: r.top - containerRect.top + r.height / 2
    }
  }
  if (anchor.kind === 'RegisterRow') {
    const el = document.getElementById(`reg-row-${anchor.reg}`)
    if (!el) return null
    const r = el.getBoundingClientRect()
    return {
      x: r.left - containerRect.left,
      y: r.top - containerRect.top + r.height / 2
    }
  }
  if (anchor.kind === 'CanvasComponent') {
    const canvasEl = archCanvas.value
    if (!canvasEl) return null
    const canvasRect = canvasEl.getBoundingClientRect()
    const scaleX = canvasRect.width / 800
    const scaleY = canvasRect.height / 450
    const layout = (LAYOUT as any)[anchor.id]
    if (!layout) return null
    const cx = 'size' in layout ? layout.x : layout.x + (layout.w ?? 0) / 2
    const cy = 'size' in layout ? layout.y + layout.size / 2 : layout.y + (layout.h ?? 0) / 2
    return {
      x: canvasRect.left - containerRect.left + cx * scaleX,
      y: canvasRect.top - containerRect.top + cy * scaleY
    }
  }
  if (anchor.kind === 'PC') {
    const idx = codeLineAddresses.value.findIndex(addr => (addr || '').toLowerCase() === anchor.pc.toLowerCase())
    if (idx >= 0) return resolveAnchor({ kind: 'CodeLineAddr', lineIndex: idx })
    return null
  }
  if (anchor.kind === 'CodeFragment') {
    const lineEl = (lineRefs.value as any)[anchor.lineIndex]
    if (!lineEl) return null
    const spanEl = lineEl.querySelector(`.fragment-highlight[data-fragment-id="${anchor.fragment}"]`) as HTMLElement | null
    if (!spanEl) return null
    const r = spanEl.getBoundingClientRect()
    return {
      x: r.left - containerRect.left + r.width / 2,
      y: r.top - containerRect.top + r.height / 2
    }
  }
  if (anchor.kind === 'FloatingToken') {
    const pos = floatingTokenPositions.value.get(anchor.tokenId)
    if (!pos) return null
    return pos
  }
  return null
}

// Canvas focus state for ADL (0=none, 1=CU/REG, 2=ALU, 3=writeback)
const canvasFocusStep = ref(0)
function setCanvasFocusStep(target: 'CU' | 'REG' | 'ALU' | 'None') {
  if (target === 'None') canvasFocusStep.value = 0
  else if (target === 'ALU') canvasFocusStep.value = 2
  else canvasFocusStep.value = 1
  drawArchitecture(canvasFocusStep.value)
}

function applySnapshotToUI(snapshot: StepSnapshot) {
  const regMap = snapshot.registers || {}
  ;(registers.value as any[]).forEach(r => {
    const key = r.name.toLowerCase()
    const val = (regMap as any)[key] ?? (regMap as any)[r.name]
    if (val !== undefined) {
      const num = typeof val === 'string' && /^0x[0-9a-fA-F]+$/.test(val) ? parseInt(val, 16) : Number(val)
      r.value = isNaN(num) ? 0 : num
    }
    r.status = ''
  })
  const f = snapshot.flags || { N: 0, Z: 0, C: 0, V: 0 }
  flags.value = { N: !!(f as any).N, Z: !!(f as any).Z, C: !!(f as any).C, V: !!(f as any).V }
  if (snapshot.memoryDelta && memoryStore.value) {
    for (const [addrStr, byteVal] of Object.entries(snapshot.memoryDelta)) {
      const addr = parseInt(addrStr.replace(/^0x/, ''), 16)
      if (!isNaN(addr) && addr >= 0 && addr < MEMORY_SIZE) (memoryStore.value as number[])[addr] = (byteVal as number) & 0xff
    }
  }
}

function formatRegisterValue(reg: RegisterRow): string {
  const v = reg.value >>> 0
  if (reg.base === 'hex') {
    return '0x' + v.toString(16).toUpperCase()
  }
  if (reg.base === 'bin') {
    return '0b' + v.toString(2)
  }
  return String(v)
}

function toggleRegisterBase(regName: string) {
  const r = registers.value.find(x => x.name === regName)
  if (!r) return
  if (r.base === 'dec') {
    r.base = 'hex'
  } else if (r.base === 'hex') {
    r.base = 'bin'
  } else {
    r.base = 'dec'
  }
}

function createTraceDriver() {
  return {
    applySnapshot(snapshot: StepSnapshot) {
      applySnapshotToUI(snapshot)
    },
    setActiveLine(index: number) {
      activeLineIndex.value = index
    },
    setCanvasFocus(target: 'CU' | 'REG' | 'ALU' | 'None') {
      setCanvasFocusStep(target)
    },
    markRegister(reg: string, mode: 'read' | 'write' | 'clear') {
      const r = (registers.value as any[]).find(x => x.name.toUpperCase() === reg.toUpperCase())
      if (r) r.status = mode === 'clear' ? '' : mode
    },
    setOverlay(from: AnchorRef, to: AnchorRef, text: string) {
      let fromPos = resolveAnchor(from)
      let toPos = resolveAnchor(to)
      if (fromPos && toPos) {
        if (from.kind === 'FloatingToken' && to.kind === 'FloatingToken') {
          const dx = toPos.x - fromPos.x
          const dy = toPos.y - fromPos.y
          const len = Math.sqrt(dx * dx + dy * dy) || 1
          const offset = 18
          fromPos = { x: fromPos.x + (dx / len) * offset, y: fromPos.y + (dy / len) * offset }
          toPos = { x: toPos.x - (dx / len) * offset, y: toPos.y - (dy / len) * offset }
        }
        demoOverlay.value = { show: true, from: fromPos, to: toPos, text }
      } else {
        demoOverlay.value.show = false
      }
    },
    wait(ms: number): Promise<void> {
      return new Promise(resolve => setTimeout(resolve, ms))
    },
    highlightCodeFragments(lineIndex: number, fragments: FragmentSpan[]) {
      const spans: FragmentHighlightSpan[] = fragments.map(f => ({ start: f.start, end: f.end, id: f.id }))
      const next = new Map(fragmentHighlights.value)
      next.set(lineIndex, spans)
      fragmentHighlights.value = next
    },
    clearFragmentHighlight() {
      fragmentHighlights.value = new Map()
    },
    async animateFragmentMove(
      lineIndex: number,
      fragments: FragmentSpan[],
      options?: { duration?: number; target?: 'codeBoxCenter' }
    ): Promise<void> {
      const containerEl = demoContainerRef.value
      const editorEl = editorWrapperRef.value
      if (!containerEl || !editorEl) return
      const containerRect = containerEl.getBoundingClientRect()
      const editorRect = editorEl.getBoundingClientRect()
      const centerX = editorRect.left - containerRect.left + editorRect.width / 2
      const centerY = editorRect.top - containerRect.top + editorRect.height / 2
      const duration = options?.duration ?? 600

      const lineEl = (lineRefs.value as any)[lineIndex] as HTMLElement | null
      if (!lineEl) return

      const spacing = 120
      const n = fragments.length
      const startX = centerX - ((n - 1) * spacing) / 2

      const tokens: FloatingTokenItem[] = []
      for (let i = 0; i < fragments.length; i++) {
        const f = fragments[i]
        const spanEl = lineEl.querySelector(`.fragment-highlight[data-fragment-id="${f.id}"]`) as HTMLElement | null
        let x: number, y: number
        if (spanEl) {
          const r = spanEl.getBoundingClientRect()
          x = r.left - containerRect.left + r.width / 2
          y = r.top - containerRect.top + r.height / 2
        } else {
          x = centerX
          y = centerY
        }
        tokens.push({
          id: f.id ?? `f${i}`,
          text: f.text,
          x,
          y,
          scale: 1,
          animating: true,
          duration
        })
      }
      floatingTokens.value = tokens
      await nextTick()

      const positions = new Map<string, { x: number; y: number }>()
      for (let i = 0; i < fragments.length; i++) {
        const f = fragments[i]
        const tid = f.id ?? `f${i}`
        positions.set(tid, { x: startX + i * spacing, y: centerY })
      }
      floatingTokenPositions.value = positions

      floatingTokens.value = tokens.map((t, i) => ({
        ...t,
        x: startX + i * spacing,
        y: centerY,
        scale: 1.8,
        animating: true,
        duration
      }))

      await new Promise<void>(resolve => setTimeout(resolve, duration))
    },
    resetFragmentState() {
      fragmentHighlights.value = new Map()
      floatingTokenPositions.value = new Map()
      floatingTokens.value = []
    }
  }
}

// Canvas Drawing Logic
const drawArchitecture = (step = 0) => {
  const canvas = archCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const w = canvas.width
  const h = canvas.height
  
  // Clear
  ctx.clearRect(0, 0, w, h)
  
  // Colors
  const COLOR_BG = '#ffffff'
  const COLOR_BOX = '#f0f2f5'
  const COLOR_BOX_ACTIVE = '#e6f7ff'
  const COLOR_TEXT = '#333'
  const COLOR_BUS = '#909399'
  const COLOR_BUS_ACTIVE = '#E6A23C' // Yellow
  const COLOR_ALU = '#f0f2f5'
  
  ctx.fillStyle = COLOR_BG
  ctx.fillRect(0, 0, w, h)
  
  // Use Constants
  const { CU, REG, ALU } = LAYOUT

  // 1. Control Unit (Left)
  drawBox(ctx, CU.x, CU.y, CU.w, CU.h, step >= 1 ? COLOR_BOX_ACTIVE : COLOR_BOX, 'Control Unit', COLOR_TEXT)
  // Subtext for CU
  ctx.fillStyle = '#666'
  ctx.font = '12px Arial'
  ctx.fillText('Instruction Decoder', CU.x + CU.w/2, CU.y + CU.h/2 + 20)
  
  // 2. Register Bank (Top Right)
  drawBox(ctx, REG.x, REG.y, REG.w, REG.h, step === 1 || step === 3 ? COLOR_BOX_ACTIVE : COLOR_BOX, 'Register Bank', COLOR_TEXT)
  
  // 3. ALU (Bottom Right)
  drawALU(ctx, ALU.x, ALU.y, ALU.size, step === 2 ? COLOR_BUS_ACTIVE : COLOR_ALU, COLOR_TEXT)
  
  // 4. Control Signals (CU -> Reg, CU -> ALU)
  // To Reg
  drawPath(ctx, [{x: CU.x + CU.w, y: CU.y + 20}, {x: REG.x, y: REG.y + 30}], COLOR_BUS, step >= 1, true) // dashed for control?
  // To ALU
  drawPath(ctx, [{x: CU.x + CU.w, y: CU.y + 80}, {x: ALU.x - ALU.size, y: ALU.y}], COLOR_BUS, step === 2, true)
  
  // 5. Bus: Reg -> ALU (Input A) - Left
  drawPath(ctx, 
    [{x: REG.x + 60, y: REG.y + REG.h}, {x: REG.x + 60, y: ALU.y - 10}, {x: ALU.x - 40, y: ALU.y}], 
    step === 1 ? COLOR_BUS_ACTIVE : COLOR_BUS,
    step === 1 // animate arrow
  )
  
  // 6. Bus: Reg -> ALU (Input B) - Right (or Immediate)
  drawPath(ctx, 
    [{x: REG.x + REG.w - 60, y: REG.y + REG.h}, {x: REG.x + REG.w - 60, y: ALU.y - 10}, {x: ALU.x + 40, y: ALU.y}], 
    step === 1 ? COLOR_BUS_ACTIVE : COLOR_BUS,
    false
  )
  
  // Text for inputs
  ctx.fillStyle = COLOR_TEXT
  ctx.font = '14px monospace'
  if (step >= 1) {
     ctx.fillText("R0 (1)", ALU.x - 80, ALU.y - 30)
     ctx.fillText("#2", ALU.x + 80, ALU.y - 30)
  }

  // 7. Bus: ALU -> Reg (Writeback)
  // Result
  drawPath(ctx, 
    [{x: ALU.x, y: ALU.y + 60}, {x: ALU.x, y: ALU.y + 100}, {x: REG.x + REG.w + 30, y: ALU.y + 100}, {x: REG.x + REG.w + 30, y: REG.y + 40}, {x: REG.x + REG.w, y: REG.y + 40}], 
    step === 3 ? '#67C23A' : COLOR_BUS,
    step === 3
  )
  
  if (step >= 2) {
      ctx.fillStyle = '#333'
      ctx.font = 'bold 16px monospace'
      ctx.fillText("Result: 3", ALU.x - 40, ALU.y + 90)
  }

  if (step >= 3) {
      // 显示写回目的寄存器的结果，帮助理解数据流向
      ctx.fillStyle = '#333'
      ctx.font = 'bold 14px monospace'
      ctx.fillText("Write R1 = 3", REG.x + REG.w + 40, REG.y + 45)
  }
}

function drawBox(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, color: string, text: string, textColor: string) {
  ctx.fillStyle = color
  ctx.strokeStyle = '#dcdfe6'
  ctx.lineWidth = 2
  ctx.fillRect(x, y, w, h)
  ctx.strokeRect(x, y, w, h)
  
  ctx.fillStyle = textColor || '#333'
  ctx.font = 'bold 16px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, x + w/2, y + h/2)
}

function drawALU(ctx: CanvasRenderingContext2D, x: number, y: number, size: number, color: string, textColor: string) {
  ctx.fillStyle = color
  ctx.strokeStyle = '#dcdfe6'
  ctx.lineWidth = 2
  
  ctx.beginPath()
  // V shape
  ctx.moveTo(x - size, y)
  ctx.lineTo(x + size, y)
  ctx.lineTo(x + 20, y + size)
  ctx.lineTo(x - 20, y + size)
  ctx.closePath()
  
  ctx.fill()
  ctx.stroke()
  
  ctx.fillStyle = textColor || '#333'
  ctx.font = 'bold 20px Arial'
  ctx.fillText('ALU', x, y + size/2)
}

function drawPath(
  ctx: CanvasRenderingContext2D,
  points: { x: number; y: number }[],
  color: string,
  active: boolean,
  isControl = false
) {
  ctx.beginPath()
  ctx.strokeStyle = color
  ctx.lineWidth = active ? 4 : 2
  if (isControl) {
    ctx.setLineDash([5, 5])
  } else {
    ctx.setLineDash([])
  }
  
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y)
  }
  ctx.stroke()
  ctx.setLineDash([]) // reset
  
  // Arrow head at end
  const last = points[points.length-1]
  const prev = points[points.length-2]
  const angle = Math.atan2(last.y - prev.y, last.x - prev.x)
  
  ctx.beginPath()
  ctx.fillStyle = color
  ctx.moveTo(last.x, last.y)
  ctx.lineTo(last.x - 10 * Math.cos(angle - Math.PI/6), last.y - 10 * Math.sin(angle - Math.PI/6))
  ctx.lineTo(last.x - 10 * Math.cos(angle + Math.PI/6), last.y - 10 * Math.sin(angle + Math.PI/6))
  ctx.fill()
}

// Overlay Logic
const updateOverlay = (targetType: 'CANVAS' | 'REGISTER' | '', targetValue: string, text: string) => {
  if (!targetType) {
    demoOverlay.value.show = false
    return
  }
  
  // 1. Get Source Position (Active Line) - 使用地址元素（.line-addr）作为箭头起点
  const activeLineEl = (lineRefs.value as any)[activeLineIndex.value]
  const containerEl = demoContainerRef.value
  
  if (!activeLineEl || !containerEl) return
  
  // 获取地址元素（.line-addr）作为箭头起点
  const lineAddrEl = activeLineEl.querySelector('.line-addr') as HTMLElement | null
  if (!lineAddrEl) return
  
  const addrRect = lineAddrEl.getBoundingClientRect()
  const containerRect = containerEl.getBoundingClientRect()
  
  // 箭头从地址左边缘出发
  const fromX = addrRect.left - containerRect.left
  const fromY = addrRect.top - containerRect.top + addrRect.height / 2
  
  let toX = 0, toY = 0
  
  if (targetType === 'CANVAS') {
     // Canvas component
     const canvasEl = archCanvas.value
     const leftPanelEl = leftPanelRef.value
     if (!canvasEl || !leftPanelEl) return
     
     const canvasRect = canvasEl.getBoundingClientRect()
     const canvasOffsetX = canvasRect.left - containerRect.left
     const canvasOffsetY = canvasRect.top - containerRect.top
     const scaleX = canvasRect.width / 800
     const scaleY = canvasRect.height / 450
     
     const layout = (LAYOUT as any)[targetValue]
     if (!layout) return
     
     if (targetValue === 'ALU') {
        toX = canvasOffsetX + layout.x * scaleX
        toY = canvasOffsetY + (layout.y + layout.size / 2) * scaleY
     } else {
        toX = canvasOffsetX + (layout.x + layout.w / 2) * scaleX
        toY = canvasOffsetY + (layout.y + layout.h / 2) * scaleY
     }
  } else if (targetType === 'REGISTER') {
     // Right panel table row
     const el = document.getElementById(`reg-row-${targetValue}`)
     if (el) {
       const rect = el.getBoundingClientRect()
       // Point to left edge of register name
       toX = rect.left - containerRect.left
       toY = rect.top - containerRect.top + rect.height/2
     } else {
       // Fallback
       console.warn('Register element not found', targetValue)
       demoOverlay.value.show = false
       return
     }
  }
  
  demoOverlay.value = {
    show: true,
    from: { x: fromX, y: fromY },
    to: { x: toX, y: toY },
    text: text
  }
}

function clearAnimationOverlayState() {
  demoOverlay.value.show = false
  fragmentHighlights.value = new Map()
  floatingTokenPositions.value = new Map()
  floatingTokens.value = []
  const f = currentTrace.value?.initialState?.flags
  if (f) {
    flags.value = { N: !!(f.N), Z: !!(f.Z), C: !!(f.C), V: !!(f.V) }
  } else {
    flags.value = { N: false, Z: false, C: false, V: false }
  }
}

function applyLeftPanelRatioHeights() {
  const el = leftPanelRef.value
  if (!el) return
  const toolbar = el.querySelector('.toolbar') as HTMLElement | null
  const toolbarH = toolbar ? toolbar.getBoundingClientRect().height : 48
  const total = el.clientHeight - toolbarH - RESIZE_HANDLE_H
  if (total <= 0) return
  const sum = EDITOR_CANVAS_RATIO[0] + EDITOR_CANVAS_RATIO[1]
  const part = total / sum
  editorHeight.value = Math.max(60, Math.round(part * EDITOR_CANVAS_RATIO[0]))
}

function applyRightPanelRatioHeights() {
  const el = rightPanelRef.value
  if (!el) return
  const total = el.clientHeight - 2 * RESIZE_HANDLE_H
  if (total <= 0) return
  const sum = FLAGS_REGISTERS_MEMORY_RATIO[0] + FLAGS_REGISTERS_MEMORY_RATIO[1] + FLAGS_REGISTERS_MEMORY_RATIO[2]
  const part = total / sum
  flagsHeight.value = Math.max(60, Math.round(part * FLAGS_REGISTERS_MEMORY_RATIO[0]))
  memoryHeight.value = Math.max(60, Math.round(part * FLAGS_REGISTERS_MEMORY_RATIO[2]))
  // Registers 占 3 份，由 flex:1 自动填充
}

onMounted(() => {
  drawArchitecture(0)
  let retries = 0
  const maxRetries = 25
  const tryApply = () => {
    const rightEl = rightPanelRef.value
    const leftEl = leftPanelRef.value
    if (rightEl?.clientHeight > 0) applyRightPanelRatioHeights()
    if (leftEl?.clientHeight > 0) applyLeftPanelRatioHeights()
    if (rightEl?.clientHeight > 0) return
    if (retries++ < maxRetries) setTimeout(tryApply, 80)
  }
  nextTick().then(() => requestAnimationFrame(tryApply))
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})

// Mock trace for demo mode (ADL-driven demo, frontend only)
const MOCK_TRACE = {
  adlVersion: ADL_VERSION,
  code: [
    { text: 'ldr r1, =0x255', addr: '0x0000' },
    { text: 'adds r0, r1, #0x5', addr: '0x0002' },
    { text: 'MOVS r1, #5', addr: '0x0004' }
  ],
  initialState: {
    registers: { r0: '0x0', r1: '0x0', r2: '0x0', r3: '0x0', r4: '0x0', r5: '0x0', r6: '0x0', r7: '0x0', r8: '0x0', r9: '0x0', r10: '0x0', r11: '0x0', r12: '0x0', r13: '0x0', r14: '0x0', r15: '0x0' },
    flags: { N: 0, Z: 0, C: 0, V: 0 }
  },
  steps: [
    {
      snapshot: { pc: '0x0000', lineCounter: 1, registers: { r0: '0x0', r1: '0x0' }, flags: { N: 0, Z: 0, C: 0, V: 0 } },
      events: [
        { type: 'SetActiveLine', by: 'index', value: 0 },
        { type: 'FocusCanvas', target: 'CU' },
        { type: 'OverlayArrow', from: { kind: 'CodeLineAddr', lineIndex: 0 }, to: { kind: 'CanvasComponent', id: 'CU' }, text: 'Decode: LDR r1, =0x255' },
        { type: 'Wait', ms: 1000 }
      ]
    },
    {
      snapshot: { pc: '0x0002', lineCounter: 2, registers: { r0: '0x0', r1: '0x255' }, flags: { N: 0, Z: 0, C: 0, V: 0 } },
      events: [
        { type: 'FocusCanvas', target: 'REG' },
        { type: 'OverlayArrow', from: { kind: 'CanvasComponent', id: 'REG' }, to: { kind: 'RegisterRow', reg: 'R1' }, text: 'Load R1 = 0x255' },
        { type: 'MarkRegister', reg: 'R1', mode: 'write' },
        { type: 'Wait', ms: 1000 }
      ]
    },
    {
      snapshot: { pc: '0x0004', lineCounter: 3, registers: { r0: '0x25A', r1: '0x255' }, flags: { N: 0, Z: 0, C: 0, V: 0 } },
      events: [
        { type: 'SetActiveLine', by: 'index', value: 1 },
        { type: 'FocusCanvas', target: 'ALU' },
        { type: 'OverlayArrow', from: { kind: 'CodeLineAddr', lineIndex: 1 }, to: { kind: 'CanvasComponent', id: 'ALU' }, text: 'ADDS r0, r1, #0x5' },
        { type: 'MarkRegister', reg: 'R1', mode: 'read' },
        { type: 'OverlayArrow', from: { kind: 'CanvasComponent', id: 'ALU' }, to: { kind: 'RegisterRow', reg: 'R0' }, text: 'ALU: 0x255 + 0x5 = 0x25A' },
        { type: 'MarkRegister', reg: 'R1', mode: 'clear' },
        { type: 'MarkRegister', reg: 'R0', mode: 'write' },
        { type: 'Wait', ms: 1000 }
      ]
    },
    {
      snapshot: { pc: '0x0006', lineCounter: 4, registers: { r0: '0x25A', r1: '0x5' }, flags: { N: 0, Z: 0, C: 0, V: 0 } },
      events: [
        { type: 'SetActiveLine', by: 'index', value: 2 },
        { type: 'FocusCanvas', target: 'REG' },
        { type: 'OverlayArrow', from: { kind: 'CodeLineAddr', lineIndex: 2 }, to: { kind: 'RegisterRow', reg: 'R1' }, text: 'MOVS r1, #5' },
        { type: 'MarkRegister', reg: 'R1', mode: 'write' },
        { type: 'HighlightCodeFragment', lineIndex: 2, fragments: [{ text: 'r1', start: 5, end: 7, id: 'dest' }, { text: '#5', start: 9, end: 11, id: 'src' }] },
        { type: 'Wait', ms: 300 },
        { type: 'AnimateFragmentMove', lineIndex: 2, fragments: [{ text: 'r1', start: 5, end: 7, id: 'dest' }, { text: '#5', start: 9, end: 11, id: 'src' }], duration: 600, target: 'codeBoxCenter' },
        { type: 'OverlayArrow', from: { kind: 'FloatingToken', tokenId: 'src' }, to: { kind: 'FloatingToken', tokenId: 'dest' }, text: '#5 → R1' },
        { type: 'Wait', ms: 1000 }
      ]
    }
  ]
} as TraceResponse

async function fetchTrace(): Promise<TraceResponse | null> {
  // Only project mode (with projectUuid) is allowed to request backend trace.
  if (!props.projectUuid) {
    return null
  }
  try {
    const url = `/api/project/trace?uuid=${encodeURIComponent(props.projectUuid)}`
    const res = await fetch(url, { method: 'GET', credentials: 'include' })
    // #region agent log
    console.log('[DEBUG-10b1d7] fetchTrace response', { ok: res.ok, status: res.status, hypothesisId: 'A' })
    // #endregion
    if (!res.ok) return null
    const data = await res.json()
    // #region agent log
    console.log('[DEBUG-10b1d7] fetchTrace data check', { adlVersion: (data as any)?.adlVersion, stepsIsArray: Array.isArray((data as any)?.steps), pass: ((data as any)?.adlVersion === ADL_VERSION && Array.isArray((data as any)?.steps)), hypothesisId: 'A' })
    // #endregion
    if ((data as any)?.adlVersion === ADL_VERSION && Array.isArray((data as any)?.steps)) return data as TraceResponse
    return null
  } catch (e) {
    // #region agent log
    console.log('[DEBUG-10b1d7] fetchTrace catch', { err: String(e), hypothesisId: 'A' })
    // #endregion
    return null
  }
}

async function runTraceAnimation(trace: TraceResponse) {
  // #region agent log
  console.log('[DEBUG-10b1d7] runTraceAnimation entered', { stepsLen: trace.steps?.length, hypothesisId: 'D' })
  // #endregion
  isAnimating.value = true
  isPlaying.value = false
  isPaused.value = false
  currentTrace.value = trace
  if (trace.initialState) applySnapshotToUI({ pc: '', lineCounter: 0, registers: trace.initialState.registers || {}, flags: trace.initialState.flags || { N: 0, Z: 0, C: 0, V: 0 } })
  if (trace.code && trace.code.length) {
    if (!props.projectUuid) {
      // Demo 模式：仍然使用 TraceResponse 中的代码文本覆盖编辑区，保持现有体验。
      code.value = trace.code.map(c => c.text).join('\n')
      await nextTick()
    } else {
      // 项目模式：保留编辑区中的源码，仅更新执行地址映射。
      executionCodeLines.value = trace.code
    }
  } else if (props.projectUuid) {
    executionCodeLines.value = null
  }
  // #region agent log
  if (props.projectUuid && trace.code?.length) {
    console.log('[DEBUG-10b1d7] before stepTo project mode', { codeLen: code.value.split('\n').length, execLinesLen: executionCodeLines.value?.length, totalSteps: trace.steps?.length, hypothesisId: 'B' })
  }
  // #endregion
  drawArchitecture(0)
  clearAnimationOverlayState()
  const driver = createTraceDriver()
  const controller = createTraceController(trace, driver, { speed: playSpeed.value })
  traceController.value = controller
  totalSteps.value = controller.totalSteps
  currentStepIndex.value = controller.currentIndex
  if (controller.totalSteps > 0) {
    currentStepIndex.value = -1
    currentStepText.value = ''
    // 点击 Run 后自动从第一步开始播放动画（从 -1 开始，playForward 会执行 step 0）
    playFromCurrent()
  } else {
    isAnimating.value = false
    currentStepText.value = ''
  }
}

async function runDemoFromMockTrace() {
  // Frontend-only demo animation using ADL MOCK_TRACE
  await runTraceAnimation(MOCK_TRACE)
}

const runDemo = async () => {
  if (isAnimating.value) return

  // Demo mode (no projectUuid): frontend-only animation, no backend calls.
  if (!props.projectUuid) {
    await runDemoFromMockTrace()
    return
  }

  // Project mode: try backend trace first, fall back to handcrafted demo.
  const trace = await fetchTrace()
  // #region agent log
  console.log('[DEBUG-10b1d7] runDemo trace result', { hasTrace: !!trace, stepsLen: trace?.steps?.length, hypothesisId: 'A' })
  // #endregion
  if (trace) {
    await runTraceAnimation(trace)
  } else {
    await runDemoFallback()
  }
}

async function playFromCurrent() {
  const controller = traceController.value
  if (!controller || totalSteps.value === 0) return
  if (isPlaying.value) return
  isPlaying.value = true
  isPaused.value = false
  isAnimating.value = true
  const playSessionId = Symbol('playSession')
  const localSession = playSessionId
  await controller.playForward({
    fromIndex: currentStepIndex.value,
    speed: playSpeed.value,
    animateWaits: true,
    shouldContinue: () => {
      return isPlaying.value && !isPaused.value && traceController.value === controller && localSession === playSessionId
    }
  })
  if (traceController.value === controller && localSession === playSessionId) {
    isPlaying.value = false
    isPaused.value = false
    isAnimating.value = false
    if (controller.currentIndex === controller.totalSteps - 1 && controller.totalSteps > 0) {
      currentStepText.value = 'Execution Completed'
      // 单步或最后一步：延迟清除 overlay/浮动 token/寄存器高亮，使用户能看清最终状态
      const clearDelay = 1200
      setTimeout(() => {
        if (traceController.value === controller) {
          clearAnimationOverlayState()
          setCanvasFocusStep('None')
          ;(registers.value as RegisterRow[]).forEach(r => { r.status = '' })
        }
        if (currentStepText.value === 'Execution Completed') currentStepText.value = ''
      }, clearDelay)
    } else {
      clearAnimationOverlayState()
      setCanvasFocusStep('None')
      ;(registers.value as RegisterRow[]).forEach(r => { r.status = '' })
    }
    currentStepIndex.value = controller.currentIndex
  }
}

function pausePlayback() {
  if (!isPlaying.value) return
  isPaused.value = true
  isPlaying.value = false
}

async function stepForward() {
  const controller = traceController.value
  if (!controller || totalSteps.value === 0) return
  if (currentStepIndex.value >= totalSteps.value - 1) return
  isPlaying.value = false
  isPaused.value = false
  await controller.stepTo(currentStepIndex.value + 1, { animateWaits: false })
  currentStepIndex.value = controller.currentIndex
}

async function stepBackward() {
  const controller = traceController.value
  if (!controller || totalSteps.value === 0) return
  if (currentStepIndex.value <= 0) {
    await controller.stepTo(0, { animateWaits: false })
    currentStepIndex.value = controller.currentIndex
    return
  }
  isPlaying.value = false
  isPaused.value = false
  await controller.stepTo(currentStepIndex.value - 1, { animateWaits: false })
  currentStepIndex.value = controller.currentIndex
}

async function resetPlayback() {
  const controller = traceController.value
  if (!controller || totalSteps.value === 0) return
  isPlaying.value = false
  isPaused.value = false
  await controller.stepTo(0, { animateWaits: false })
  currentStepIndex.value = controller.currentIndex
  currentStepText.value = ''
}

async function runDemoFallback() {
  const fallbackTrace: TraceResponse = {
    adlVersion: ADL_VERSION,
    steps: [
      {
        snapshot: {
          pc: '0x0000',
          lineCounter: 1,
          registers: { r0: '0x1', r1: '0x0' },
          flags: { N: 0, Z: 0, C: 0, V: 0 }
        },
        events: [
          { type: 'SetActiveLine', by: 'index', value: 0 },
          { type: 'FocusCanvas', target: 'CU' },
          {
            type: 'OverlayArrow',
            from: { kind: 'CodeLineAddr', lineIndex: 0 },
            to: { kind: 'CanvasComponent', id: 'CU' },
            text: 'Step 1: Decode instruction (Control Unit)'
          },
          { type: 'Wait', ms: 1200 }
        ]
      },
      {
        snapshot: {
          pc: '0x0002',
          lineCounter: 2,
          registers: { r0: '0x1', r1: '0x0' },
          flags: { N: 0, Z: 0, C: 0, V: 0 }
        },
        events: [
          { type: 'SetActiveLine', by: 'index', value: 0 },
          { type: 'FocusCanvas', target: 'REG' },
          {
            type: 'OverlayArrow',
            from: { kind: 'RegisterRow', reg: 'R0' },
            to: { kind: 'RegisterRow', reg: 'R0' },
            text: 'Step 2: Read operand R0'
          },
          { type: 'MarkRegister', reg: 'R0', mode: 'read' },
          { type: 'Wait', ms: 1200 }
        ]
      },
      {
        snapshot: {
          pc: '0x0004',
          lineCounter: 3,
          registers: { r0: '0x1', r1: '0x3' },
          flags: { N: 0, Z: 0, C: 0, V: 0 }
        },
        events: [
          { type: 'FocusCanvas', target: 'ALU' },
          {
            type: 'OverlayArrow',
            from: { kind: 'CanvasComponent', id: 'ALU' },
            to: { kind: 'CanvasComponent', id: 'ALU' },
            text: 'Step 3: ALU Execution (R0 + #2)'
          },
          { type: 'Wait', ms: 1200 }
        ]
      },
      {
        snapshot: {
          pc: '0x0006',
          lineCounter: 4,
          registers: { r0: '0x1', r1: '0x3' },
          flags: { N: 0, Z: 0, C: 0, V: 0 }
        },
        events: [
          { type: 'FocusCanvas', target: 'REG' },
          {
            type: 'OverlayArrow',
            from: { kind: 'CanvasComponent', id: 'REG' },
            to: { kind: 'RegisterRow', reg: 'R1' },
            text: 'Step 4: Write back result to R1'
          },
          { type: 'MarkRegister', reg: 'R1', mode: 'write' },
          { type: 'Wait', ms: 1200 }
        ]
      }
    ]
  }
  await runTraceAnimation(fallbackTrace)
}

</script>

<style scoped>
.demo-container {
  display: flex;
  height: 100%;
  min-height: 0;
  padding-top: 12px;
  padding-bottom: 12px;
  gap: 0;
  background-color: #f5f7fa;
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
}

/* 左右边缘拖拽条 */
.resize-edge {
  position: absolute;
  top: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 20;
  transition: background-color 0.2s;
}

.resize-edge-left {
  left: 0;
}

.resize-edge-right {
  right: 0;
}

.resize-edge::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 40px;
  background: #c0c4cc;
  border-radius: 1px;
  transition: height 0.2s, background-color 0.2s;
}

.resize-edge:hover {
  background: rgba(64, 158, 255, 0.15);
}

.resize-edge:hover::after {
  height: 60px;
  background: #409eff;
}

.left-panel {
  flex: 1;
  min-width: 0;
  background: #2d2d2d;
  color: #ccc;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.overlay-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 100; /* Top most */
}

.animated-path {
  animation: dash 1s linear infinite;
}

@keyframes dash {
  to {
    stroke-dashoffset: -15;
  }
}

.arrow-label text {
  font-family: 'Fira Code', 'Consolas', monospace;
  pointer-events: none;
}

.toolbar {
  padding: 10px;
  background: #333;
  border-bottom: 1px solid #444;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.addr-hint {
  margin-left: auto;
}

.step-info {
  font-weight: bold;
}

.playback-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 160px;
}

.speed-label {
  font-size: 12px;
  color: #ddd;
}

.speed-slider {
  flex: 1;
  max-width: 160px;
}

.speed-value {
  font-size: 12px;
  color: #eee;
  min-width: 44px;
  text-align: right;
}

.step-summary {
  font-size: 12px;
  color: #ddd;
  white-space: nowrap;
}

.step-counter {
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}

.editor-wrapper {
  display: flex;
  flex: none;
  overflow: auto;
}

.canvas-container {
  flex: 1;
  min-height: 0;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  border-top: 1px solid #dcdfe6;
}

.canvas-header {
  padding: 5px 10px;
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.canvas-zoom-controls .zoom-label {
  min-width: 52px;
}

.canvas-zoom-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.canvas-zoom-inner {
  position: relative;
}

.canvas-zoom-content {
  width: 800px;
  height: 450px;
  transform-origin: 0 0;
}

.canvas-zoom-content canvas {
  display: block;
  width: 800px;
  height: 450px;
}

canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.code-lines {
  flex: 1;
  padding: 10px 0;
  background: #2d2d2d;
}

.code-line {
  display: flex;
  align-items: center;
  height: 28px;
  line-height: 28px;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  transition: background-color 0.3s;
  cursor: default;
}

.code-line:hover {
  background-color: #333842;
}

.code-line.active-line {
  background-color: #3e4451;
}

.code-line.active-line .line-number {
  color: #fff;
  font-weight: bold;
}

.code-line.active-line .line-content {
  color: #e5c07b;
  font-weight: bold;
}

.code-line.active-line .line-addr {
  color: #e5c07b;
  font-weight: bold;
}

.line-number {
  display: inline-block;
  min-width: 40px;
  padding: 0 10px;
  text-align: right;
  color: #636d83;
  user-select: none;
  background: #1e1e1e;
  border-right: 1px solid #444;
  flex-shrink: 0;
}

.line-content {
  padding: 0 12px;
  color: #abb2bf;
  white-space: pre;
  cursor: default;
  flex: 1;
  min-width: 0;
}

.line-content .fragment-highlight {
  background: rgba(230, 163, 60, 0.5);
  color: #e5c07b;
  padding: 1px 2px;
  border-radius: 2px;
}

.floating-tokens-layer {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 110;
}

.floating-token {
  position: absolute;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  font-weight: bold;
  color: #e5c07b;
  background: rgba(45, 45, 45, 0.95);
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.line-addr {
  flex-shrink: 0;
  min-width: 56px;
  padding: 0 10px;
  text-align: right;
  color: #636d83;
  font-family: 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  border-left: 1px solid #444;
  background: #252526;
}

/* 可拖拽分隔条 */
.resize-handle {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  position: relative;
  flex-shrink: 0;
  z-index: 10;
  transition: background-color 0.2s;
}

.resize-handle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 40px;
  background: #c0c4cc;
  border-radius: 1px;
  transition: height 0.2s, background-color 0.2s;
}

.resize-handle:hover {
  background: rgba(64, 158, 255, 0.1);
}

.resize-handle:hover::after {
  height: 60px;
  background: #409eff;
}

.right-panel {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 面板区域通用 */
.panel-section {
  flex: none;
  min-height: 0;
  overflow: hidden;
}

/* Registers 区域弹性填充 */
.panel-section.section-flex {
  flex: 1;
  min-height: 0;
}

/* 卡片填满 section */
.full-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.full-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

/* 水平分隔条（上下拖拽） */
.resize-handle-h {
  height: 6px;
  cursor: row-resize;
  background: transparent;
  position: relative;
  flex-shrink: 0;
  z-index: 10;
  transition: background-color 0.2s;
}

.resize-handle-h::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  height: 2px;
  width: 40px;
  background: #c0c4cc;
  border-radius: 1px;
  transition: width 0.2s, background-color 0.2s;
}

.resize-handle-h:hover {
  background: rgba(64, 158, 255, 0.1);
}

.resize-handle-h:hover::after {
  width: 60px;
  background: #409eff;
}

/* Flags Styles */
.flags-container {
  display: flex;
  justify-content: space-around;
  padding: 4px 0;
}

.flag-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #f0f2f5;
  padding: 6px 10px;
  border-radius: 4px;
  width: 40px;
  border: 1px solid #dcdfe6;
  transition: all 0.3s;
}

/* 紧凑卡片头 */
::deep(.el-card__header) {
  padding: 8px 12px;
}
::deep(.el-card__body) {
  padding: 8px 12px;
}

.flag-item.active {
  background: #e6a23c;
  color: #fff;
  border-color: #e6a23c;
  transform: scale(1.1);
}

.flag-name {
  font-weight: bold;
  font-size: 14px;
  margin-bottom: 4px;
}

.flag-val {
  font-family: monospace;
}

/* Registers 两列网格 */
.registers-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 10px;
}

.register-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  background: #fafafa;
  transition: all 0.3s ease;
}

.register-name-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.register-cell.row-read {
  background-color: rgba(230, 162, 60, 0.08);
  border-color: rgba(230, 162, 60, 0.3);
}

.register-cell.row-write {
  background-color: rgba(103, 194, 58, 0.08);
  border-color: rgba(103, 194, 58, 0.3);
}

.register-name {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-icon {
  font-size: 14px;
}
.status-icon.read { color: #E6A23C; } /* Warning color for Read */
.status-icon.write { color: #67C23A; } /* Success color for Write */

.register-value-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.value-display {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.value-display.read {
  background-color: rgba(230, 162, 60, 0.2);
  color: #E6A23C;
  font-weight: bold;
  transform: scale(1.05);
}

.value-display.write {
  background-color: rgba(103, 194, 58, 0.2);
  color: #67C23A;
  font-weight: bold;
  transform: scale(1.05);
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.45);
}

.value-base-bars {
  display: flex;
  gap: 2px;
}

.base-bar {
  width: 9px;
  height: 3px;
  border-radius: 999px;
  background-color: #e5e7eb;
  transition: all 0.2s ease;
  display: none;
}

.base-bar-dec {
  background-color: #409eff;
}

.base-bar-hex {
  background-color: #e6a23c;
}

.base-bar-bin {
  background-color: #67c23a;
}

.base-bar.active {
  display: block;
  transform: translateY(-1px);
}

.card-header:has(.memory-range-controls) {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.memory-range-controls {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.memory-range-controls .range-label {
  font-size: 12px;
  color: #909399;
}
.memory-range-controls .memory-addr-input {
  width: 72px;
}
.memory-range-controls .memory-addr-input .el-input__inner {
  font-family: monospace;
  font-size: 12px;
}
.memory-range-controls .memory-count-select {
  width: 56px;
}

.memory-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.memory-cell {
  background: #f0f2f5;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
}

.addr {
  color: #909399;
}
</style>

