<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { runBase64Codec, type Base64RunOptions } from './api/base64'
import { ApiError, runJsonFormat, type JsonRunOptions } from './api/tools'
import {
  buildPreferencesPayload,
  devLogin,
  fetchExecutions,
  fetchFavorites,
  fetchMe,
  fetchPreferences,
  logout,
  savePreferences,
  setFavorite,
  type ExecutionSummary,
  type UserProfile
} from './api/platform'
import { t, toggleLocale } from './i18n'

type OutputTab = 'raw' | 'tree' | 'error'
type RunState = 'idle' | 'running' | 'succeeded' | 'failed'
type ToolName = 'json-format' | 'base64' | 'timestamp' | 'regex-test'

const selectedTool = ref<ToolName>('json-format')
const input = ref('{"b":1,"a":{"d":4,"c":3}}')
const output = ref('')
const errorMessage = ref('')
const activeTab = ref<OutputTab>('raw')
const runState = ref<RunState>('idle')
const durationMs = ref<number | null>(null)
const currentUser = ref<UserProfile | null>(null)
const favorites = ref<string[]>([])
const executions = ref<ExecutionSummary[]>([])
const authBusy = ref(false)
const options = ref<JsonRunOptions>({
  indent: 2,
  sortKeys: true,
  ensureAscii: false
})
const base64Options = ref<Base64RunOptions>({
  mode: 'encode',
  charset: 'utf-8'
})

const tools = computed(() => [
  {
    name: 'json-format' as const,
    glyph: '{}',
    title: t('tools.jsonFormat.title'),
    meta: t('tools.jsonFormat.meta'),
    active: selectedTool.value === 'json-format',
    favorite: favorites.value.includes('json-format'),
    enabled: true
  },
  {
    name: 'timestamp' as const,
    glyph: 'T',
    title: t('tools.timestamp.title'),
    meta: t('tools.timestamp.meta'),
    active: false,
    favorite: false,
    enabled: false
  },
  {
    name: 'base64' as const,
    glyph: '64',
    title: t('tools.base64.title'),
    meta: t('tools.base64.meta'),
    active: selectedTool.value === 'base64',
    favorite: favorites.value.includes('base64'),
    enabled: true
  },
  {
    name: 'regex-test' as const,
    glyph: '.*',
    title: t('tools.regex.title'),
    meta: t('tools.regex.meta'),
    active: false,
    favorite: false,
    enabled: false
  }
])

const currentToolTitle = computed(() =>
  selectedTool.value === 'base64' ? t('tools.base64.title') : t('tools.jsonFormat.title')
)
const currentToolKicker = computed(() =>
  selectedTool.value === 'base64' ? t('workspace.base64Kicker') : t('workspace.jsonKicker')
)
const currentToolDescription = computed(() =>
  selectedTool.value === 'base64'
    ? t('workspace.base64Description')
    : t('workspace.jsonDescription')
)
const inputBytes = computed(() => new TextEncoder().encode(input.value).length)
const outputBytes = computed(() => new TextEncoder().encode(output.value).length)
const hasOutput = computed(() => output.value.length > 0)
const isSignedIn = computed(() => currentUser.value !== null)
const favoriteCurrentTool = computed(() => favorites.value.includes(selectedTool.value))
const displayName = computed(() => currentUser.value?.display_name || currentUser.value?.email || '')
const stateLabel = computed(() => {
  if (runState.value === 'running') return t('status.running')
  if (runState.value === 'succeeded') return `${t('status.succeeded')} · ${durationMs.value ?? 0}ms`
  if (runState.value === 'failed') return t('status.failed')
  return t('status.ready')
})
const recentExecutions = computed(() => executions.value.slice(0, 5))
const outputPlaceholder = computed(() =>
  selectedTool.value === 'base64' ? t('placeholders.base64Output') : t('placeholders.rawOutput')
)
const treeOutput = computed(() => {
  if (!output.value) return ''
  try {
    return JSON.stringify(JSON.parse(output.value), null, 2)
  } catch {
    return output.value
  }
})

onMounted(() => {
  void loadAccount()
})

async function loadAccount() {
  try {
    currentUser.value = await fetchMe()
    if (currentUser.value) {
      await loadUserResources()
    }
  } catch {
    currentUser.value = null
  }
}

async function loadUserResources() {
  const [favoriteList, preferences, executionList] = await Promise.all([
    fetchFavorites(),
    fetchPreferences(),
    fetchExecutions()
  ])
  favorites.value = favoriteList
  executions.value = executionList

  const jsonOptions = preferences.tool_options?.['json-format'] as Partial<JsonRunOptions> | undefined
  if (jsonOptions) {
    options.value = {
      indent: typeof jsonOptions.indent === 'number' ? jsonOptions.indent : options.value.indent,
      sortKeys:
        typeof jsonOptions.sortKeys === 'boolean' ? jsonOptions.sortKeys : options.value.sortKeys,
      ensureAscii:
        typeof jsonOptions.ensureAscii === 'boolean'
          ? jsonOptions.ensureAscii
          : options.value.ensureAscii
    }
  }
}

async function signIn() {
  authBusy.value = true
  try {
    currentUser.value = await devLogin()
    await loadUserResources()
  } catch {
    window.location.href = '/api/auth/github/start'
  } finally {
    authBusy.value = false
  }
}

async function signOut() {
  authBusy.value = true
  try {
    await logout()
    currentUser.value = null
    favorites.value = []
    executions.value = []
  } finally {
    authBusy.value = false
  }
}

async function toggleFavorite() {
  if (!currentUser.value) {
    await signIn()
    return
  }
  favorites.value = await setFavorite(selectedTool.value, !favoriteCurrentTool.value)
}

async function runTool() {
  runState.value = 'running'
  errorMessage.value = ''
  activeTab.value = 'raw'

  try {
    if (selectedTool.value === 'base64') {
      const response = await runBase64Codec(input.value, base64Options.value)
      output.value = response.result.text
      durationMs.value = response.duration_ms
    } else {
      const response = await runJsonFormat(input.value, options.value)
      output.value = response.result.formatted
      durationMs.value = response.duration_ms
    }
    runState.value = 'succeeded'
    if (currentUser.value && selectedTool.value === 'json-format') {
      await savePreferences(buildPreferencesPayload(options.value))
      executions.value = await fetchExecutions()
    }
  } catch (error) {
    output.value = ''
    durationMs.value = null
    activeTab.value = 'error'
    runState.value = 'failed'
    errorMessage.value = error instanceof ApiError ? error.message : t('errors.unexpectedToolRunFailure')
  }
}

function selectTool(toolName: ToolName, enabled: boolean) {
  if (!enabled || selectedTool.value === toolName) return
  selectedTool.value = toolName
  clearInput()
  useSampleInput()
}

function clearInput() {
  input.value = ''
  output.value = ''
  errorMessage.value = ''
  runState.value = 'idle'
  durationMs.value = null
}

function useSampleInput() {
  input.value = selectedTool.value === 'base64' ? 'Hello, YuKit' : '{\n  "hello": "YuKit"\n}'
}

function resetOptions() {
  if (selectedTool.value === 'base64') {
    base64Options.value = { mode: 'encode', charset: 'utf-8' }
  } else {
    options.value = { indent: 2, sortKeys: true, ensureAscii: false }
  }
}

async function copyOutput() {
  if (!output.value) return
  await navigator.clipboard?.writeText(output.value)
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand" aria-label="YuKit">
        <span class="brand-mark">Y</span>
        <span>YuKit</span>
      </div>
      <button class="command-search" type="button">
        <span>{{ t('toolbar.search') }}</span>
        <kbd>Ctrl K</kbd>
      </button>
      <div class="top-actions">
        <button
          class="language-toggle"
          type="button"
          :title="t('toolbar.languageButtonTitle')"
          :aria-label="t('toolbar.languageButtonTitle')"
          @click="toggleLocale"
        >
          {{ t('toolbar.languageSwitch') }}
        </button>
        <button class="icon-button" type="button" :title="t('toolbar.help')" :aria-label="t('toolbar.help')">?</button>
        <button class="icon-button" type="button" :title="t('toolbar.theme')" :aria-label="t('toolbar.theme')">◐</button>
        <button
          v-if="!isSignedIn"
          class="primary-button"
          type="button"
          :disabled="authBusy"
          @click="signIn"
        >
          {{ t('auth.signIn') }}
        </button>
        <button v-else class="user-pill" type="button" :disabled="authBusy" @click="signOut">
          {{ displayName }}
        </button>
      </div>
    </header>

    <aside class="sidebar">
      <section>
        <div class="section-label">{{ t('sections.discover') }}</div>
        <div class="chips">
          <button class="chip active" type="button">{{ t('tags.all') }}</button>
          <button class="chip" type="button">{{ t('tags.format') }}</button>
          <button class="chip" type="button">{{ t('tags.codec') }}</button>
          <button class="chip" type="button">{{ t('tags.time') }}</button>
          <button class="chip" type="button">{{ t('tags.text') }}</button>
        </div>
      </section>

      <section>
        <div class="section-label">{{ t('sections.favorites') }}</div>
      </section>

      <nav class="tool-list" :aria-label="t('aria.tools')">
        <button
          v-for="tool in tools"
          :key="tool.title"
          class="tool-item"
          :class="{ active: tool.active }"
          type="button"
          :disabled="!tool.enabled"
          @click="selectTool(tool.name, tool.enabled)"
        >
          <span class="tool-glyph">{{ tool.glyph }}</span>
          <span class="tool-copy">
            <span class="tool-title">{{ tool.title }}</span>
            <span class="tool-meta">{{ tool.meta }}</span>
          </span>
          <span class="favorite">{{ tool.favorite ? '★' : '☆' }}</span>
        </button>
      </nav>

      <div class="system-badge">{{ t('system.healthy') }}</div>
    </aside>

    <main class="workspace">
      <section class="workspace-heading">
        <div>
          <div class="kicker">{{ currentToolKicker }}</div>
          <h1>{{ currentToolTitle }}</h1>
          <p>{{ currentToolDescription }}</p>
        </div>
        <div class="heading-actions">
          <button
            class="icon-button"
            type="button"
            :title="t('actions.favorite')"
            :aria-label="t('actions.favorite')"
            @click="toggleFavorite"
          >
            {{ favoriteCurrentTool ? '★' : '☆' }}
          </button>
          <button class="primary-button run-button" type="button" :disabled="runState === 'running'" @click="runTool">
            {{ runState === 'running' ? t('actions.running') : t('actions.run') }}
          </button>
        </div>
      </section>

      <section class="meta-row" :aria-label="t('aria.executionStatus')">
        <span class="badge">{{ t('badges.public') }}</span>
        <span class="badge">{{ t('badges.sync') }}</span>
        <span class="badge" :class="{ good: runState === 'succeeded', danger: runState === 'failed' }">
          {{ stateLabel }}
        </span>
        <span class="badge">{{ t('badges.inputNotStored') }}</span>
        <button class="badge action" type="button" :disabled="!hasOutput" @click="copyOutput">
          {{ t('actions.copyResult') }}
        </button>
      </section>

      <section class="tool-workspace">
        <div class="io-stack">
          <section class="panel">
            <header class="panel-head">
              <span>{{ t('panels.input') }}</span>
              <span class="panel-tools">
                <button type="button" @click="useSampleInput">{{ t('actions.sample') }}</button>
                <button type="button" @click="clearInput">{{ t('actions.clear') }}</button>
                <span>{{ inputBytes }} B</span>
              </span>
            </header>
            <textarea
              v-model="input"
              class="code-input"
              spellcheck="false"
              :aria-label="t('aria.toolInput')"
            />
          </section>

          <section class="panel">
            <header class="panel-head">
              <span>{{ t('panels.output') }}</span>
              <span class="panel-tabs">
                <button type="button" :class="{ active: activeTab === 'raw' }" @click="activeTab = 'raw'">
                  {{ t('tabs.raw') }}
                </button>
                <button type="button" :class="{ active: activeTab === 'tree' }" @click="activeTab = 'tree'">
                  {{ t('tabs.tree') }}
                </button>
                <button type="button" :class="{ active: activeTab === 'error' }" @click="activeTab = 'error'">
                  {{ t('tabs.error') }}
                </button>
                <span>{{ outputBytes }} B</span>
              </span>
            </header>
            <pre v-if="activeTab === 'raw'" class="code-output">{{ output || outputPlaceholder }}</pre>
            <pre v-else-if="activeTab === 'tree'" class="code-output">{{ treeOutput || t('placeholders.treeOutput') }}</pre>
            <div v-else class="error-output">
              <strong>{{ errorMessage || t('errors.noLatestError') }}</strong>
              <span>{{ t('errors.sanitized') }}</span>
            </div>
          </section>
        </div>

        <aside class="panel options-panel">
          <header class="panel-head">
            <span>{{ t('panels.options') }}</span>
            <button type="button" @click="resetOptions">{{ t('actions.reset') }}</button>
          </header>
          <div class="options-body">
            <template v-if="selectedTool === 'json-format'">
            <label class="field">
              <span>{{ t('options.indentSize') }}</span>
              <select v-model.number="options.indent">
                <option :value="0">{{ t('options.compact') }}</option>
                <option :value="2">{{ t('options.spaces2') }}</option>
                <option :value="4">{{ t('options.spaces4') }}</option>
                <option :value="8">{{ t('options.spaces8') }}</option>
              </select>
            </label>

            <label class="switch-row">
              <span>
                <strong>{{ t('options.sortKeys') }}</strong>
                <small>{{ t('options.sortKeysHelp') }}</small>
              </span>
              <input v-model="options.sortKeys" type="checkbox" />
            </label>

            <label class="switch-row">
              <span>
                <strong>{{ t('options.ensureAscii') }}</strong>
                <small>{{ t('options.ensureAsciiHelp') }}</small>
              </span>
              <input v-model="options.ensureAscii" type="checkbox" />
            </label>
            </template>

            <template v-else>
            <label class="field">
              <span>{{ t('options.codecMode') }}</span>
              <select v-model="base64Options.mode">
                <option value="encode">{{ t('options.encode') }}</option>
                <option value="decode">{{ t('options.decode') }}</option>
              </select>
            </label>

            <label class="field">
              <span>{{ t('options.charset') }}</span>
              <select v-model="base64Options.charset">
                <option value="utf-8">UTF-8</option>
              </select>
            </label>
            </template>

            <div class="history-note">
              <span>{{ t('options.historyPolicy') }}</span>
              <p>{{ t('options.historyPolicyHelp') }}</p>
            </div>

            <div v-if="isSignedIn" class="history-list">
              <span>{{ t('options.recentRuns') }}</span>
              <p v-if="recentExecutions.length === 0">{{ t('options.noSavedRuns') }}</p>
              <button
                v-for="item in recentExecutions"
                :key="item.id"
                class="history-item"
                type="button"
              >
                <strong>{{ item.tool }}</strong>
                <small>{{ item.status }} · {{ item.duration_ms ?? 0 }}ms</small>
              </button>
            </div>
          </div>
        </aside>
      </section>
    </main>
  </div>
</template>
