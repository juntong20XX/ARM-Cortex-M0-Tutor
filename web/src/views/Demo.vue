<template>
  <div class="demo-container">
    <div class="left-panel">
      <div class="toolbar">
        <el-button type="primary" size="small" @click="runDemo" :disabled="isAnimating">
          <el-icon><VideoPlay /></el-icon> 演示执行 (ADD 2 r0 r1)
        </el-button>
        <el-tag v-if="currentStepText" type="warning" class="step-info">{{ currentStepText }}</el-tag>
      </div>
      <div class="editor-wrapper">
        <div class="line-numbers">
          <div v-for="n in lineCount" :key="n" :class="{ 'active-line': n === 4 }">{{ n }}</div>
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
         <canvas ref="archCanvas" width="800" height="300"></canvas>
      </div>
    </div>
    <div class="right-panel">
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
              <div class="register-name">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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

const tableRowClassName = ({ row }) => {
  if (row.status === 'read') {
    return 'row-read'
  } else if (row.status === 'write') {
    return 'row-write'
  }
  return ''
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
  
  // 1. Control Unit (Left)
  const cuX = 50, cuY = 100, cuW = 120, cuH = 100
  drawBox(ctx, cuX, cuY, cuW, cuH, step >= 1 ? COLOR_BOX_ACTIVE : COLOR_BOX, 'Control Unit', COLOR_TEXT)
  
  // 2. Register Bank (Top Right)
  const regX = 300, regY = 40, regW = 200, regH = 60
  drawBox(ctx, regX, regY, regW, regH, step === 1 || step === 3 ? COLOR_BOX_ACTIVE : COLOR_BOX, 'Register Bank', COLOR_TEXT)
  
  // 3. ALU (Bottom Right)
  const aluX = 400, aluY = 200, aluSize = 60
  drawALU(ctx, aluX, aluY, aluSize, step === 2 ? COLOR_BUS_ACTIVE : COLOR_ALU, COLOR_TEXT)
  
  // 4. Control Signals (CU -> Reg, CU -> ALU)
  // To Reg
  drawPath(ctx, [{x: cuX + cuW, y: cuY + 20}, {x: regX, y: regY + 30}], COLOR_BUS, step >= 1)
  // To ALU
  drawPath(ctx, [{x: cuX + cuW, y: cuY + 80}, {x: aluX - aluSize, y: aluY}], COLOR_BUS, step === 2)

  // 5. Bus: Reg -> ALU (Input A) - Left
  drawPath(ctx, 
    [{x: regX + 40, y: regY + regH}, {x: regX + 40, y: aluY - 10}, {x: aluX - 30, y: aluY}], 
    step === 1 ? COLOR_BUS_ACTIVE : COLOR_BUS,
    step === 1 // animate arrow
  )
  
  // 6. Bus: Reg -> ALU (Input B) - Right (or Immediate)
  drawPath(ctx, 
    [{x: regX + 160, y: regY + regH}, {x: regX + 160, y: aluY - 10}, {x: aluX + 30, y: aluY}], 
    step === 1 ? COLOR_BUS_ACTIVE : COLOR_BUS,
    false
  )
  
  // Text for inputs
  ctx.fillStyle = COLOR_TEXT
  ctx.font = '12px monospace'
  if (step >= 1) {
     ctx.fillText("R0 (1)", aluX - 60, aluY - 20)
     ctx.fillText("#2", aluX + 50, aluY - 20)
  }

  // 7. Bus: ALU -> Reg (Writeback)
  // Result
  drawPath(ctx, 
    [{x: aluX, y: aluY + 50}, {x: aluX, y: aluY + 80}, {x: regX + regW + 20, y: aluY + 80}, {x: regX + regW + 20, y: regY + 30}, {x: regX + regW, y: regY + 30}], 
    step === 3 ? '#67C23A' : COLOR_BUS,
    step === 3
  )
  
  if (step >= 2) {
      ctx.fillStyle = '#333'
      ctx.font = 'bold 14px monospace'
      ctx.fillText("Result: 3", aluX - 30, aluY + 70)
  }
}

function drawBox(ctx, x, y, w, h, color, text, textColor) {
  ctx.fillStyle = color
  ctx.strokeStyle = '#dcdfe6'
  ctx.lineWidth = 2
  ctx.fillRect(x, y, w, h)
  ctx.strokeRect(x, y, w, h)
  
  ctx.fillStyle = textColor || '#333'
  ctx.font = '14px Arial'
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
  ctx.lineTo(x + 10, y + size)
  ctx.lineTo(x - 10, y + size)
  ctx.closePath()
  
  ctx.fill()
  ctx.stroke()
  
  ctx.fillStyle = textColor || '#333'
  ctx.font = 'bold 16px Arial'
  ctx.fillText('ALU', x, y + size/2)
}

function drawPath(ctx, points, color, active) {
  ctx.beginPath()
  ctx.strokeStyle = color
  ctx.lineWidth = active ? 4 : 2
  
  ctx.moveTo(points[0].x, points[0].y)
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(points[i].x, points[i].y)
  }
  ctx.stroke()
  
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
  
  // Step 1: Read
  currentStepText.value = 'Step 1: 读取源操作数 (R0, #2) -> 总线传输'
  const r0 = registers.value.find(r => r.name === 'R0')
  if (r0) r0.status = 'read'
  drawArchitecture(1)
  
  await sleep(1500)
  
  // Step 2: ALU
  currentStepText.value = 'Step 2: ALU 执行加法 (1 + 2 = 3)'
  // Calc result and update flags
  const result = 3
  flags.value.N = result < 0
  flags.value.Z = result === 0
  // C and V remain false for 1+2
  
  drawArchitecture(2)
  
  await sleep(1500)
  
  // Step 3: Write
  currentStepText.value = 'Step 3: 结果回写寄存器 (R1)'
  if (r0) r0.status = '' 
  const r1 = registers.value.find(r => r.name === 'R1')
  if (r1) {
    r1.status = 'write'
    r1.value = result
  }
  drawArchitecture(3)
  
  await sleep(1500)
  
  // Finish
  currentStepText.value = '执行完成'
  if (r1) r1.status = ''
  drawArchitecture(0)
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
  flex: 1; /* Adjust flex to share space with canvas */
  min-height: 200px;
  overflow: auto;
  font-family: 'Fira Code', monospace;
  border-bottom: 1px solid #444;
}

.canvas-container {
  height: 340px; /* Fixed height for visualization */
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
