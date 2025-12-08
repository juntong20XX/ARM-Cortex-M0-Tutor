<template>
  <section class="panel">
    <p class="eyebrow">ARM Cortex-M0 Tutorial</p>
    <h1 class="title">ARM Cortex-M0 Tutorial</h1>
    <p class="lead">
      This frontend receives OAuth login callbacks. Follow backend configuration
      and redirect to <code>/login-oauth/{provider_name}</code> to complete the
      login flow.
    </p>
    <ul class="hint-list">
      <li>After redirect from the auth service, query params like code and state are provided.</li>
      <li>The page automatically forwards to backend <code>/api/login-oauth/{provider_name}</code> for validation.</li>
      <li>If you need to reprocess, refresh or click the retry button.</li>
    </ul>
  </section>
</template>

