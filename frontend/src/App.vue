<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { runBase64Codec, type Base64RunOptions } from './api/base64'
import { runRegexTest, type RegexFlag, type RegexRunOptions } from './api/regex'
import { runTextHash, type TextHashRunOptions } from './api/textHash'
import { runTimestampConverter, type TimestampRunOptions } from './api/timestamp'
import { ApiError, runJsonFormat, type JsonRunOptions } from './api/tools'
import {
  buildPreferencesPayload,
  fetchExecution,
  devLogin,
  fetchExecutions,
  fetchFavorites,
  fetchMe,
  fetchPreferences,
  isTerminalExecutionStatus,
  logout,
  savePreferences,
  setFavorite,
  type ExecutionSummary,
  type UserProfile
} from './api/platform'
import { t, toggleLocale } from './i18n'

type OutputTab = 'raw' | 'tree' | 'error'
type RunState = 'idle' | 'queued' | 'running' | 'succeeded' | 'failed' | 'timed_out' | 'canceled'
type ToolName = 'json-format' | 'base64' | 'timestamp' | 'regex-test' | 'text-hash'

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
const timestampOptions = ref<TimestampRunOptions>({
  mode: 'from-unix'
})
const regexOptions = ref<RegexRunOptions>({
  pattern: String.raw`\b\w+\b`,
  flags: [],
  maxMatches: 50,
  timeoutMs: 50
})
const textHashOptions = ref<TextHashRunOptions>({
  algorithm: 'sha256'
})

const regexFlagOptions: Array<{ value: RegexFlag; labelKey: string }> = [
  { value: 'ignorecase', labelKey: 'options.flagIgnoreCase' },
  { value: 'multiline', labelKey: 'options.flagMultiline' },
  { value: 'dotall', labelKey: 'options.flagDotall' },
  { value: 'ascii', labelKey: 'options.flagAscii' },
  { value: 'verbose', labelKey: 'options.flagVerbose' }
]

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
    active: selectedTool.value === 'timestamp',
    favorite: favorites.value.includes('timestamp'),
    enabled: true
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
    active: selectedTool.value === 'regex-test',
    favorite: favorites.value.includes('regex-test'),
    enabled: true
  },
  {
    name: 'text-hash' as const,
    glyph: '#',
    title: t('tools.textHash.title'),
    meta: t('tools.textHash.meta'),
    active: selectedTool.value === 'text-hash',
    favorite: favorites.value.includes('text-hash'),
    enabled: true
  }
])

const currentToolTitle = computed(() =>
  selectedTool.value === 'base64'
    ? t('tools.base64.title')
    : selectedTool.value === 'timestamp'
      ? t('tools.timestamp.title')
      : selectedTool.value === 'regex-test'
        ? t('tools.regex.title')
        : selectedTool.value === 'text-hash'
          ? t('tools.textHash.title')
          : t('tools.jsonFormat.title')
)
const currentToolKicker = computed(() =>
  selectedTool.value === 'base64'
    ? t('workspace.base64Kicker')
    : selectedTool.value === 'timestamp'
      ? t('workspace.timestampKicker')
      : selectedTool.value === 'regex-test'
        ? t('workspace.regexKicker')
        : selectedTool.value === 'text-hash'
          ? t('workspace.textHashKicker')
          : t('workspace.jsonKicker')
)
const currentToolDescription = computed(() =>
  selectedTool.value === 'base64'
    ? t('workspace.base64Description')
    : selectedTool.value === 'timestamp'
      ? t('workspace.timestampDescription')
      : selectedTool.value === 'regex-test'
        ? t('workspace.regexDescription')
        : selectedTool.value === 'text-hash'
          ? t('workspace.textHashDescription')
          : t('workspace.jsonDescription')
)
const currentAccessBadge = computed(() =>
  selectedTool.value === 'text-hash' ? t('badges.authenticated') : t('badges.public')
)
const currentModeBadge = computed(() =>
  selectedTool.value === 'text-hash' ? t('badges.async') : t('badges.sync')
)
const inputBytes = computed(() => new TextEncoder().encode(input.value).length)
const outputBytes = computed(() => new TextEncoder().encode(output.value).length)
const hasOutput = computed(() => output.value.length > 0)
const isSignedIn = computed(() => currentUser.value !== null)
const favoriteCurrentTool = computed(() => favorites.value.includes(selectedTool.value))
const displayName = computed(() => currentUser.value?.display_name || currentUser.value?.email || '')
const stateLabel = computed(() => {
  if (runState.value === 'queued') return t('status.queued')
  if (runState.value === 'running') return t('status.running')
  if (runState.value === 'succeeded') return `${t('status.succeeded')} · ${durationMs.value ?? 0}ms`
  if (runState.value === 'failed') return t('status.failed')
  if (runState.value === 'timed_out') return t('status.timedOut')
  if (runState.value === 'canceled') return t('status.canceled')
  return t('status.ready')
})
const recentExecutions = computed(() => executions.value.slice(0, 5))
const outputPlaceholder = computed(() =>
  selectedTool.value === 'base64'
    ? t('placeholders.base64Output')
    : selectedTool.value === 'timestamp'
      ? t('placeholders.timestampOutput')
      : selectedTool.value === 'regex-test'
        ? t('placeholders.regexOutput')
        : selectedTool.value === 'text-hash'
          ? t('placeholders.textHashOutput')
          : t('placeholders.rawOutput')
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
    if (selectedTool.value === 'text-hash') {
      await runAsyncTextHash()
      return
    } else if (selectedTool.value === 'base64') {
      const response = await runBase64Codec(input.value, base64Options.value)
      output.value = response.result.text
      durationMs.value = response.duration_ms
    } else if (selectedTool.value === 'timestamp') {
      const response = await runTimestampConverter(input.value, timestampOptions.value)
      output.value = [
        `${t('output.isoUtc')}: ${response.result.iso_utc}`,
        `${t('output.unixSeconds')}: ${response.result.unix_seconds}`,
        `${t('output.unixMilliseconds')}: ${response.result.unix_milliseconds}`
      ].join('\n')
      durationMs.value = response.duration_ms
    } else if (selectedTool.value === 'regex-test') {
      const response = await runRegexTest(input.value, regexOptions.value)
      output.value = JSON.stringify(response.result, null, 2)
      durationMs.value = response.duration_ms
    } else {
      const response = await runJsonFormat(input.value, options.value)
      output.value = response.result.formatted
      durationMs.value = response.duration_ms
    }
    runState.value = 'succeeded'
    if (currentUser.value && selectedTool.value === 'json-format') {
      await savePreferences(buildPreferencesPayload(options.value))
    }
    if (currentUser.value) {
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

async function runAsyncTextHash() {
  if (!currentUser.value) {
    await signIn()
  }
  if (!currentUser.value) {
    throw new Error(t('errors.authRequired'))
  }

  const response = await runTextHash(input.value, textHashOptions.value)
  runState.value = 'queued'
  output.value = `${t('status.queued')} · ${response.execution_id}`

  const execution = await pollExecution(response.execution_id)
  durationMs.value = execution.duration_ms

  if (execution.status === 'succeeded') {
    output.value = JSON.stringify(execution.result, null, 2)
    runState.value = 'succeeded'
    executions.value = await fetchExecutions()
    return
  }

  output.value = ''
  activeTab.value = 'error'
  runState.value = execution.status as RunState
  errorMessage.value = execution.error_message || execution.error_code || execution.status
  executions.value = await fetchExecutions()
}

async function pollExecution(executionId: string) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const execution = await fetchExecution(executionId)
    runState.value = execution.status === 'queued' ? 'queued' : 'running'
    if (isTerminalExecutionStatus(execution.status)) {
      return execution
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1000))
  }
  throw new Error(t('errors.executionPollingTimedOut'))
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
  if (selectedTool.value === 'base64') {
    input.value = 'Hello, YuKit'
  } else if (selectedTool.value === 'timestamp') {
    input.value = timestampOptions.value.mode === 'from-unix' ? '1700000000' : '2023-11-14T22:13:20Z'
  } else if (selectedTool.value === 'regex-test') {
    input.value = 'alpha-100\nbeta-205\ngamma'
    regexOptions.value.pattern = String.raw`(?P<name>[a-z]+)-(\d+)`
  } else if (selectedTool.value === 'text-hash') {
    input.value = 'YuKit'
  } else {
    input.value = '{\n  "hello": "YuKit"\n}'
  }
}

function resetOptions() {
  if (selectedTool.value === 'base64') {
    base64Options.value = { mode: 'encode', charset: 'utf-8' }
  } else if (selectedTool.value === 'timestamp') {
    timestampOptions.value = { mode: 'from-unix' }
  } else if (selectedTool.value === 'regex-test') {
    regexOptions.value = {
      pattern: String.raw`\b\w+\b`,
      flags: [],
      maxMatches: 50,
      timeoutMs: 50
    }
  } else if (selectedTool.value === 'text-hash') {
    textHashOptions.value = { algorithm: 'sha256' }
  } else {
    options.value = { indent: 2, sortKeys: true, ensureAscii: false }
  }
}

function toggleRegexFlag(flag: RegexFlag) {
  regexOptions.value.flags = regexOptions.value.flags.includes(flag)
    ? regexOptions.value.flags.filter((item) => item !== flag)
    : [...regexOptions.value.flags, flag]
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
          <button
            class="primary-button run-button"
            type="button"
            :disabled="runState === 'running' || runState === 'queued'"
            @click="runTool"
          >
            {{ runState === 'running' || runState === 'queued' ? t('actions.running') : t('actions.run') }}
          </button>
        </div>
      </section>

      <section class="meta-row" :aria-label="t('aria.executionStatus')">
        <span class="badge">{{ currentAccessBadge }}</span>
        <span class="badge">{{ currentModeBadge }}</span>
        <span
          class="badge"
          :class="{
            good: runState === 'succeeded',
            warning: runState === 'queued' || runState === 'running',
            danger: runState === 'failed' || runState === 'timed_out' || runState === 'canceled'
          }"
        >
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

            <template v-else-if="selectedTool === 'base64'">
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

            <template v-else-if="selectedTool === 'timestamp'">
            <label class="field">
              <span>{{ t('options.timestampMode') }}</span>
              <select v-model="timestampOptions.mode" @change="useSampleInput">
                <option value="from-unix">{{ t('options.fromUnix') }}</option>
                <option value="from-iso">{{ t('options.fromIso') }}</option>
              </select>
            </label>
            </template>

            <template v-else-if="selectedTool === 'text-hash'">
            <label class="field">
              <span>{{ t('options.hashAlgorithm') }}</span>
              <select v-model="textHashOptions.algorithm">
                <option value="sha256">SHA-256</option>
                <option value="sha512">SHA-512</option>
                <option value="md5">MD5</option>
              </select>
            </label>
            </template>

            <template v-else>
            <label class="field">
              <span>{{ t('options.regexPattern') }}</span>
              <textarea
                v-model="regexOptions.pattern"
                class="pattern-input"
                rows="4"
                spellcheck="false"
                :aria-label="t('options.regexPattern')"
              />
            </label>

            <fieldset class="field flag-group">
              <legend>{{ t('options.regexFlags') }}</legend>
              <label
                v-for="flag in regexFlagOptions"
                :key="flag.value"
                class="switch-row compact"
              >
                <span>
                  <strong>{{ t(flag.labelKey) }}</strong>
                </span>
                <input
                  type="checkbox"
                  :checked="regexOptions.flags.includes(flag.value)"
                  @change="toggleRegexFlag(flag.value)"
                />
              </label>
            </fieldset>

            <label class="field">
              <span>{{ t('options.maxMatches') }}</span>
              <input v-model.number="regexOptions.maxMatches" min="1" max="200" type="number" />
            </label>

            <label class="field">
              <span>{{ t('options.timeoutMs') }}</span>
              <select v-model.number="regexOptions.timeoutMs">
                <option :value="25">25ms</option>
                <option :value="50">50ms</option>
                <option :value="100">100ms</option>
                <option :value="250">250ms</option>
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
