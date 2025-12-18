<template>
  <div class="demo-container" ref="demoContainerRef">
    <div class="left-panel" ref="leftPanelRef">
      <div class="toolbar">
        <el-button type="primary" size="small" @click="runDemo" :disabled="isAnimating">
          <el-icon><VideoPlay /></el-icon> 演示执行 (ADD 2 r0 r1)
        </el-button>
        <el-tag v-if="currentStepText" type="warning" class="step-info">{{ currentStepText }}</el-tag>
      </div>
      <div class="editor-wrapper">
        <div class="line-numbers">
          <div v-for="n in lineCount" :key="n" :class="{ 'active-line': n === 4 }" ref="activeLineRef">{{ n }}</div>
        </div>
        <prism-editor
          class="my-editor"
          v-model="code"
          :highlight="highlighter"
          line-numbers
          readonly
        ></prism-editor>
      </div>
      <div class="canvas-container">
         <div class="canvas-header">MCU Architecture & Data Bus</div>
         <canvas ref="archCanvas" width="800" height="450"></canvas>
      </div>
    </div>
    <div class="right-panel" ref="rightPanelRef">
      <!-- Flags Card (New) -->
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>标志位 (Flags)</span>
          </div>
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

      <el-card class="box-card mt-4">
        <template #header>
          <div class="card-header">
            <span>寄存器 (Registers)</span>
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

      <el-card class="box-card mt-4">
        <template #header>
          <div class="card-header">
            <span>内存 (Memory)</span>
          </div>
        </template>
        <div class="memory-grid">
           <!-- 简化展示部分内存 -->
           <div v-for="(val, index) in memory" :key="index" class="memory-cell">
             <span class="addr">0x{{ index.toString(16).padStart(4, '0') }}:</span>
             <span class="val">{{ val }}</span>
           </div>
        </div>
      </el-card>
    </div>

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
import { ref, computed, onMounted, nextTick } from 'vue'
import { PrismEditor } from 'vue-prism-editor'
import 'vue-prism-editor/dist/prismeditor.min.css'
import Prism from 'prismjs'
import 'prismjs/themes/prism-tomorrow.css'
import { VideoPlay, View, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const code = ref('\nMOV 1 r0\n\nADD 2 r0 r1\n')

const lineCount = computed(() => {
  return code.value.split('\n').length
})

const highlighter = (code) => {
  return Prism.highlight(code, Prism.languages.clike, 'clike')
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
const activeLineRef = ref(null) 

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
  
  // 1. Get Source Position (Active Line)
  const activeLineEl = document.querySelector('.active-line')
  const containerEl = demoContainerRef.value
  
  if (!activeLineEl || !containerEl) return
  
  const lineRect = activeLineEl.getBoundingClientRect()
  const containerRect = containerEl.getBoundingClientRect()
  
  // Calculate relative to demo-container
  const fromX = lineRect.right - containerRect.left + 5 // Start a bit to the right of line number
  const fromY = lineRect.top - containerRect.top + lineRect.height / 2
  
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
  currentStepText.value = 'Step 1: 指令译码 & 读取操作数'
  const r0 = registers.value.find(r => r.name === 'R0')
  if (r0) r0.status = 'read'
  drawArchitecture(1)
  
  // Arrow: Code -> R0 (in Table) - showing we are reading R0
  await nextTick()
  updateOverlay('REGISTER', 'R0', 'Read R0')
  
  await sleep(1500)
  
  // Step 2: ALU Execute
  currentStepText.value = 'Step 2: ALU 执行 (1 + 2)'
  const result = 3
  flags.value.N = result < 0
  flags.value.Z = result === 0
  
  drawArchitecture(2)
  updateOverlay('CANVAS', 'ALU', 'Execute')
  
  await sleep(1500)
  
  // Step 3: Write Back
  currentStepText.value = 'Step 3: 结果回写 (R1)'
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
  currentStepText.value = '执行完成'
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
  padding: 20px;
  gap: 20px;
  background-color: #f5f7fa;
  position: relative; /* Anchor for Overlay */
}

.left-panel {
  flex: 1;
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
  flex: 1; 
  min-height: 200px;
  overflow: auto;
  font-family: 'Fira Code', monospace;
  border-bottom: 1px solid #444;
}

.canvas-container {
  height: 450px; 
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

.line-numbers {
  padding: 10px 0;
  background: #1e1e1e;
  border-right: 1px solid #444;
  text-align: right;
  min-width: 40px;
  user-select: none;
  color: #888;
}

.line-numbers div {
  padding: 0 10px;
  height: 24px;
  line-height: 24px;
  font-size: 14px;
}

.active-line {
  background-color: #3e4451;
  color: #fff;
  font-weight: bold;
}

.my-editor {
  background: #2d2d2d;
  color: #ccc;
  font-family: 'Fira Code', monospace;
  font-size: 14px;
  line-height: 24px;
  padding: 10px;
  flex: 1;
}

/* Override prism editor styles */
:deep(.prism-editor__textarea) {
  outline: none;
}
:deep(.prism-editor__editor) {
  white-space: pre !important;
}

.right-panel {
  width: 350px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mt-4 {
  margin-top: 16px;
}

/* Flags Styles */
.flags-container {
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
}

.flag-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #f0f2f5;
  padding: 8px 12px;
  border-radius: 4px;
  width: 40px;
  border: 1px solid #dcdfe6;
  transition: all 0.3s;
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
