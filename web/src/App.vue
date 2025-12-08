<script setup>
import {RouterLink, RouterView} from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand">
        <span class="brand-mark"/>
        <div>
          <p class="brand-name">ARM Cortex-M0</p>
          <p class="brand-sub">Home</p>
        </div>
      </div>
      <nav class="nav">
        <RouterLink to="/">Home</RouterLink>
      </nav>
    </header>

    <RouterView/>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(135deg, #2563eb, #60a5fa);
}

.brand-name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}

.brand-sub {
  margin-top: 2px;
  color: #6b7280;
  font-size: 13px;
}

.nav a {
  color: #2563eb;
  font-weight: 600;
}

.nav a:hover {
  text-decoration: underline;
}
</style>
