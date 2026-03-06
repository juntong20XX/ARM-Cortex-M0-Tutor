<script setup>
import {RouterLink, RouterView} from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="app-header-inner">
        <div class="brand">
          <span class="brand-mark"/>
          <div>
            <p class="brand-name">ARM Cortex-M0</p>
            <p class="brand-sub">Home</p>
          </div>
        </div>
        <nav class="nav">
          <RouterLink to="/" exact-active-class="nav-active">Home</RouterLink>
          <RouterLink to="/project/list" active-class="nav-active">Project</RouterLink>
          <RouterLink to="/config" active-class="nav-active">Config</RouterLink>
        </nav>
      </div>
    </header>

    <div class="app-view">
      <RouterView/>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  gap: 2vh;
  flex: 1;
  min-height: 0;
}

.app-view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.app-header {
  width: 100%;
}

.app-header-inner {
  width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.2vh 1.5vw;
  min-height: 5vh;
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

.nav {
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav a {
  color: #4b5563;
  font-weight: 600;
  font-size: 14px;
  padding: 6px 14px;
  border-radius: 8px;
  text-decoration: none;
  transition: background-color 0.2s, color 0.2s;
}

.nav a:hover {
  background-color: #f3f4f6;
  color: #2563eb;
}

.nav a.nav-active {
  background-color: #eff6ff;
  color: #2563eb;
}
</style>
