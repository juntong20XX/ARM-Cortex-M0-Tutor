<template>
  <div class="demo-container" ref="demoContainerRef" :style="{ paddingLeft: paddingLeft + 'px', paddingRight: paddingRight + 'px' }">
    <!-- 左边缘拖拽条 -->
    <div class="resize-edge resize-edge-left" @mousedown.prevent="startEdgeResize('left', $event)"></div>

    <div class="left-panel" ref="leftPanelRef">
      <div class="toolbar">
        <el-button type="primary" size="small" @click="runDemo" :disabled="isAnimating">
          <el-icon><VideoPlay /></el-icon> Run Demo (ADD 2 r0 r1)
        </el-button>
        <el-tag v-if="currentStepText" type="warning" class="step-info">{{ currentStepText }}</el-tag>
      </div>
      <div class="editor-wrapper" :style="{ height: editorHeight + 'px' }">
        <div class="code-lines">
          <div
            v-for="(line, index) in codeLines"
            :key="index"
            :ref="el => setLineRef(el, index)"
            class="code-line"
            :class="{ 'active-line': index === activeLineIndex }"
          >
            <span class="line-number">{{ index + 1 }}</span>
            <label class="line-content">{{ line || '\u00A0' }}</label>
          </div>
        </div>
      </div>
      <div class="resize-handle-h" @mousedown.prevent="startVertResize('editor-canvas', $event)"></div>
      <div class="canvas-container">
         <div class="canvas-header">MCU Architecture & Data Bus</div>
         <canvas ref="archCanvas" width="800" height="450"></canvas>
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
              <el-tag size="small" type="info">R1 = R0 + 2</el-tag>
            </div>
          </template>
          <el-table :data="registers" style="width: 100%" size="small" border :row-class-name="tableRowClassName">
            <el-table-column prop="name" label="Register" width="100">
              <template #default="scope">
                <div class="register-name" :id="'reg-row-' + scope.row.name">
                  {{ scope.row.name }}
                  <el-icon v-if="scope.row.status === 'read'" class="status-icon read"><View /></el-icon>
                  <el-icon v-if="scope.row.status === 'write'" class="status-icon write"><Edit /></el-icon>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="value" label="Value">
              <template #default="scope">
                <span :class="['value-display', scope.row.status]">
                  {{ scope.row.value }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <div class="resize-handle-h" @mousedown.prevent="startVertResize('registers-memory', $event)"></div>

      <!-- Memory Section -->
      <div class="panel-section" :style="{ height: memoryHeight + 'px' }">
        <el-card class="box-card full-card">
          <template #header>
            <div class="card-header"><span>Memory</span></div>
          </template>
          <div class="memory-grid">
            <div v-for="(val, index) in memory" :key="index" class="memory-cell">
              <span class="addr">0x{{ index.toString(16).padStart(4, '0') }}:</span>
              <span class="val">{{ val }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 右边缘拖拽条 -->
    <div class="resize-edge resize-edge-right" @mousedown.prevent="startEdgeResize('right', $event)"></div>

    <!-- Overlay Layer for Arrows (Moved to Container Level) -->
    <svg v-if="demoOverlay.show" class="overlay-svg">
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
        refX="10" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#F56C6C" />
        </marker>
      </defs>
      <path :d="arrowPath" stroke="#F56C6C" stroke-width="3" fill="none" marker-end="url(#arrowhead)" stroke-dasharray="10 5" class="animated-path"/>
      <text :x="(demoOverlay.from.x + demoOverlay.to.x)/2" :y="(demoOverlay.from.y + demoOverlay.to.y)/2 - 10" fill="#F56C6C" font-weight="bold" text-anchor="middle" class="arrow-text">{{ demoOverlay.text }}</text>
    </svg>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { VideoPlay, View, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const code = ref('\nMOV 1 r0\n\nADD 2 r0 r1\n')

const codeLines = computed(() => {
  return code.value.split('\n')
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

const registers = ref(
  Array.from({ length: 14 }, (_, i) => ({
    name: `R${i}`,
    value: i === 0 ? 1 : 0,
    status: '' // 'read' | 'write' | ''
  }))
)

// Flags state
const flags = ref({
  N: false, // Negative
  Z: false, // Zero
  C: false, // Carry
  V: false  // Overflow
})

const memory = ref(Array(16).fill(0))
const isAnimating = ref(false)
const currentStepText = ref('')
const archCanvas = ref(null)
const leftPanelRef = ref(null)
const rightPanelRef = ref(null)
const demoContainerRef = ref(null)

// ====== 拖拽调整面板尺寸 ======
const rightPanelWidth = ref(350)
const paddingLeft = ref(12)
const paddingRight = ref(12)

// 左面板：编辑器高度（代码行按内容自动 + 一些余量）
const editorHeight = ref(180)
// 右面板：Flags 区域高度、Memory 区域高度，Registers 用 flex:1
const flagsHeight = ref(110)
const memoryHeight = ref(200)

// 通用拖拽状态
let dragCtx = null

const lockDrag = (cursor) => {
  document.body.style.userSelect = 'none'
  document.body.style.cursor = cursor
}

const unlockDrag = () => {
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

// --- 水平拖拽（左右面板） ---
const startResize = (e) => {
  dragCtx = { type: 'col', startX: e.clientX, startValue: rightPanelWidth.value }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  lockDrag('col-resize')
}

// --- 垂直拖拽（上下组件） ---
const startVertResize = (type, e) => {
  let startValue
  if (type === 'editor-canvas') startValue = editorHeight.value
  else if (type === 'flags-registers') startValue = flagsHeight.value
  else if (type === 'registers-memory') startValue = memoryHeight.value

  dragCtx = { type, startY: e.clientY, startValue }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  lockDrag('row-resize')
}

// --- 边缘拖拽（左右边距） ---
const startEdgeResize = (side, e) => {
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
const onDrag = (e) => {
  if (!dragCtx) return

  if (dragCtx.type === 'edge-left') {
    // 左边缘：向右拖增大 padding
    const dx = e.clientX - dragCtx.startX
    paddingLeft.value = Math.max(0, Math.min(300, dragCtx.startValue + dx))
  } else if (dragCtx.type === 'edge-right') {
    // 右边缘：向左拖增大 padding
    const dx = e.clientX - dragCtx.startX
    paddingRight.value = Math.max(0, Math.min(300, dragCtx.startValue - dx))
  } else if (dragCtx.type === 'col') {
    // 水平：调整右面板宽度
    if (!demoContainerRef.value) return
    const containerRect = demoContainerRef.value.getBoundingClientRect()
    const newWidth = containerRect.right - e.clientX - paddingRight.value
    rightPanelWidth.value = Math.max(180, Math.min(containerRect.width * 0.6, newWidth))
  } else {
    // 垂直：调整组件高度
    const dy = e.clientY - dragCtx.startY
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
  const controlX = from.x + dx * 0.5 // Adjust curve control point
  const controlY = from.y + dy * 0.1
  
  return `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`
})

const tableRowClassName = ({ row }) => {
  if (row.status === 'read') {
    return 'row-read'
  } else if (row.status === 'write') {
    return 'row-write'
  }
  return ''
}

// Architecture Layout Constants (Scaled Up)
const LAYOUT = {
  CU: { x: 60, y: 150, w: 140, h: 120 },
  REG: { x: 350, y: 50, w: 260, h: 80 },
  ALU: { x: 480, y: 280, size: 80 }
}

// Canvas Drawing Logic
const drawArchitecture = (step = 0) => {
  const canvas = archCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
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
  ctx.font = '10px Arial'
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
}

function drawBox(ctx, x, y, w, h, color, text, textColor) {
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

function drawALU(ctx, x, y, size, color, textColor) {
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

function drawPath(ctx, points, color, active, isControl = false) {
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
const updateOverlay = (targetType, targetValue, text) => {
  if (!targetType) {
    demoOverlay.value.show = false
    return
  }
  
  // 1. Get Source Position (Active Line) - 使用行号元素精确定位
  const activeLineEl = lineRefs.value[activeLineIndex.value]
  const containerEl = demoContainerRef.value
  
  if (!activeLineEl || !containerEl) return
  
  // 获取行号元素（.line-number）作为箭头起点
  const lineNumEl = activeLineEl.querySelector('.line-number')
  if (!lineNumEl) return
  
  const numRect = lineNumEl.getBoundingClientRect()
  const containerRect = containerEl.getBoundingClientRect()
  
  // 箭头从行号右边缘出发（数字和代码中间）
  const fromX = numRect.right - containerRect.left
  const fromY = numRect.top - containerRect.top + numRect.height / 2
  
  let toX = 0, toY = 0
  
  if (targetType === 'CANVAS') {
     // Canvas component
     const canvasEl = archCanvas.value
     const leftPanelEl = leftPanelRef.value
     if (!canvasEl || !leftPanelEl) return
     
     const canvasRect = canvasEl.getBoundingClientRect()
     // We need to account that canvas is inside left-panel, which is inside demo-container
     const canvasOffsetX = canvasRect.left - containerRect.left
     const canvasOffsetY = canvasRect.top - containerRect.top
     
     const layout = LAYOUT[targetValue]
     if (!layout) return
     
     if (targetValue === 'ALU') {
        toX = layout.x + canvasOffsetX
        toY = layout.y + layout.size/2 + canvasOffsetY
     } else {
        toX = layout.x + layout.w / 2 + canvasOffsetX
        toY = layout.y + layout.h / 2 + canvasOffsetY
     }
  } else if (targetType === 'REGISTER') {
     // Right panel table row
     // Wait for next tick to ensure ID exists? It should exist if rendered.
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

onMounted(() => {
  drawArchitecture(0)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})

const runDemo = async () => {
  if (isAnimating.value) return
  isAnimating.value = true
  
  registers.value.forEach(r => r.status = '')
  registers.value[1].value = 0 
  
  // Reset Flags
  flags.value = { N: false, Z: false, C: false, V: false }

  // Step 0: Reset
  drawArchitecture(0)
  demoOverlay.value.show = false
  
  // Step 1: Fetch/Decode & Read
  currentStepText.value = 'Step 1: Decode & Read Operands'
  const r0 = registers.value.find(r => r.name === 'R0')
  if (r0) r0.status = 'read'
  drawArchitecture(1)
  
  // Arrow: Code -> R0 (in Table) - showing we are reading R0
  await nextTick()
  updateOverlay('REGISTER', 'R0', 'Read R0')
  
  await sleep(1500)
  
  // Step 2: ALU Execute
  currentStepText.value = 'Step 2: ALU Execution (1 + 2)'
  const result = 3
  flags.value.N = result < 0
  flags.value.Z = result === 0
  
  drawArchitecture(2)
  updateOverlay('CANVAS', 'ALU', 'Execute')
  
  await sleep(1500)
  
  // Step 3: Write Back
  currentStepText.value = 'Step 3: Write Back (R1)'
  if (r0) r0.status = '' 
  const r1 = registers.value.find(r => r.name === 'R1')
  if (r1) {
    r1.status = 'write'
    r1.value = result
  }
  drawArchitecture(3)
  await nextTick()
  updateOverlay('REGISTER', 'R1', 'Write R1')
  
  await sleep(1500)
  
  // Finish
  currentStepText.value = 'Execution Completed'
  if (r1) r1.status = ''
  drawArchitecture(0)
  demoOverlay.value.show = false
  isAnimating.value = false
  setTimeout(() => currentStepText.value = '', 2000)
}

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

</script>

<style scoped>
.demo-container {
  display: flex;
  height: 100vh;
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

.arrow-text {
  font-family: sans-serif;
  text-shadow: 0 0 3px white;
}

.toolbar {
  padding: 10px;
  background: #333;
  border-bottom: 1px solid #444;
  display: flex;
  align-items: center;
  gap: 10px;
}

.step-info {
  font-weight: bold;
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
:deep(.el-card__header) {
  padding: 8px 12px;
}
:deep(.el-card__body) {
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

/* Register Table Styles */
.register-name {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-icon {
  font-size: 14px;
}
.status-icon.read { color: #E6A23C; } /* Warning color for Read */
.status-icon.write { color: #67C23A; } /* Success color for Write */

.value-display {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.value-display.read {
  background-color: rgba(230, 162, 60, 0.2);
  color: #E6A23C;
  font-weight: bold;
  transform: scale(1.1);
}

.value-display.write {
  background-color: rgba(103, 194, 58, 0.2);
  color: #67C23A;
  font-weight: bold;
  transform: scale(1.1);
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.5);
}

/* Element Plus Table Row Highlights */
:deep(.el-table .row-read) {
  background-color: rgba(230, 162, 60, 0.05) !important;
}
:deep(.el-table .row-write) {
  background-color: rgba(103, 194, 58, 0.05) !important;
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
