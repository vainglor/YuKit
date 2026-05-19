<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import { runBase64Codec, type Base64RunOptions } from './api/base64'
import { runRegexTest, type RegexFlag, type RegexRunOptions } from './api/regex'
import { runTextHash, type TextHashRunOptions } from './api/textHash'
import { runTimestampConverter, type TimestampRunOptions } from './api/timestamp'
import { ApiError, runJsonFormat, type JsonRunOptions } from './api/tools'
import {
  apiBaseUrl,
  buildPreferencesPayload,
  fetchExecution,
  devLogin,
  fetchAuthOptions,
  fetchExecutions,
  fetchFavorites,
  fetchMe,
  fetchPreferences,
  isTerminalExecutionStatus,
  logout,
  savePreferences,
  setFavorite,
  type ExecutionSummary,
  type AuthOptions,
  type UserProfile
} from './api/platform'
import { preferredLoginMethod } from './authFlow'
import {
  filterTools,
  nextStylePreference,
  nextTheme,
  serializeExecutionResult,
  type StylePreference,
  type ThemePreference,
  type ToolTag
} from './interactions'
import { t, toggleLocale } from './i18n'

type OutputTab = 'raw' | 'tree' | 'error'
type RunState = 'idle' | 'queued' | 'running' | 'succeeded' | 'failed' | 'timed_out' | 'canceled'
type ToolName = 'json-format' | 'base64' | 'timestamp' | 'regex-test' | 'text-hash'
type CommandId = 'run' | 'copy' | 'theme' | 'style' | 'help' | 'refresh-status'
type SystemStatus = 'unknown' | 'checking' | 'healthy' | 'unavailable'
type SelectId = 'indent' | 'codec-mode' | 'charset' | 'timestamp-mode' | 'hash-algorithm' | 'regex-timeout'
type CustomSelectOption = { value: string | number; label: string }

const selectedTool = ref<ToolName>('json-format')
const activeTag = ref<ToolTag>('all')
const commandOpen = ref(false)
const commandQuery = ref('')
const commandInput = ref<HTMLInputElement | null>(null)
const helpOpen = ref(false)
const openSelect = ref<SelectId | null>(null)
const themePreference = ref<ThemePreference>(readStoredTheme())
const stylePreference = ref<StylePreference>(readStoredStyle())
const copyStatus = ref<'idle' | 'copied' | 'failed'>('idle')
const systemStatus = ref<SystemStatus>('unknown')
const systemBusy = ref(false)
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
const authDialogOpen = ref(false)
const authLoaded = ref(false)
const authOptions = ref<AuthOptions>({ dev_login: false, github: false, email: false })
const authError = ref('')
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

const tagOptions: Array<{ value: ToolTag; labelKey: string }> = [
  { value: 'all', labelKey: 'tags.all' },
  { value: 'format', labelKey: 'tags.format' },
  { value: 'codec', labelKey: 'tags.codec' },
  { value: 'time', labelKey: 'tags.time' },
  { value: 'text', labelKey: 'tags.text' }
]

const toolNames: ToolName[] = ['json-format', 'timestamp', 'base64', 'regex-test', 'text-hash']
const indentChoices = computed<CustomSelectOption[]>(() => [
  { value: 0, label: t('options.compact') },
  { value: 2, label: t('options.spaces2') },
  { value: 4, label: t('options.spaces4') },
  { value: 8, label: t('options.spaces8') }
])
const base64ModeChoices = computed<CustomSelectOption[]>(() => [
  { value: 'encode', label: t('options.encode') },
  { value: 'decode', label: t('options.decode') }
])
const charsetChoices = computed<CustomSelectOption[]>(() => [{ value: 'utf-8', label: 'UTF-8' }])
const timestampModeChoices = computed<CustomSelectOption[]>(() => [
  { value: 'from-unix', label: t('options.fromUnix') },
  { value: 'from-iso', label: t('options.fromIso') }
])
const hashAlgorithmChoices = computed<CustomSelectOption[]>(() => [
  { value: 'sha256', label: 'SHA-256' },
  { value: 'sha512', label: 'SHA-512' },
  { value: 'md5', label: 'MD5' }
])
const regexTimeoutChoices = computed<CustomSelectOption[]>(() => [
  { value: 25, label: '25ms' },
  { value: 50, label: '50ms' },
  { value: 100, label: '100ms' },
  { value: 250, label: '250ms' }
])

const tools = computed(() => [
  {
    name: 'json-format' as const,
    glyph: '{}',
    title: t('tools.jsonFormat.title'),
    meta: t('tools.jsonFormat.meta'),
    tags: ['format'] as const,
    active: selectedTool.value === 'json-format',
    favorite: favorites.value.includes('json-format'),
    enabled: true
  },
  {
    name: 'timestamp' as const,
    glyph: 'T',
    title: t('tools.timestamp.title'),
    meta: t('tools.timestamp.meta'),
    tags: ['time'] as const,
    active: selectedTool.value === 'timestamp',
    favorite: favorites.value.includes('timestamp'),
    enabled: true
  },
  {
    name: 'base64' as const,
    glyph: '64',
    title: t('tools.base64.title'),
    meta: t('tools.base64.meta'),
    tags: ['codec'] as const,
    active: selectedTool.value === 'base64',
    favorite: favorites.value.includes('base64'),
    enabled: true
  },
  {
    name: 'regex-test' as const,
    glyph: '.*',
    title: t('tools.regex.title'),
    meta: t('tools.regex.meta'),
    tags: ['text'] as const,
    active: selectedTool.value === 'regex-test',
    favorite: favorites.value.includes('regex-test'),
    enabled: true
  },
  {
    name: 'text-hash' as const,
    glyph: '#',
    title: t('tools.textHash.title'),
    meta: t('tools.textHash.meta'),
    tags: ['text'] as const,
    active: selectedTool.value === 'text-hash',
    favorite: favorites.value.includes('text-hash'),
    enabled: true
  }
])

const visibleTools = computed(() => filterTools(tools.value, '', activeTag.value))
const favoriteToolItems = computed(() => tools.value.filter((tool) => tool.favorite))
const commandToolResults = computed(() => filterTools(tools.value, commandQuery.value, 'all'))
const currentTool = computed(() => tools.value.find((tool) => tool.name === selectedTool.value))
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
const preferredAuthMethod = computed(() => preferredLoginMethod(authOptions.value))
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
const themeButtonTitle = computed(() =>
  themePreference.value === 'light'
    ? t('theme.switchToDark')
    : themePreference.value === 'dark'
      ? t('theme.switchToSystem')
      : t('theme.switchToLight')
)
const themeStatusLabel = computed(() =>
  themePreference.value === 'light'
    ? t('theme.light')
    : themePreference.value === 'dark'
      ? t('theme.dark')
      : t('theme.system')
)
const styleButtonTitle = computed(() =>
  stylePreference.value === 'island' ? t('style.switchToDefault') : t('style.switchToIsland')
)
const styleStatusLabel = computed(() =>
  stylePreference.value === 'island' ? t('style.island') : t('style.default')
)
const systemStatusLabel = computed(() => {
  if (systemStatus.value === 'checking') return t('system.checking')
  if (systemStatus.value === 'healthy') return t('system.healthy')
  if (systemStatus.value === 'unavailable') return t('system.unavailable')
  return t('system.refresh')
})
const systemTone = computed(() =>
  systemStatus.value === 'healthy'
    ? 'good'
    : systemStatus.value === 'unavailable'
      ? 'danger'
      : systemStatus.value === 'checking'
        ? 'warning'
        : ''
)
const copyStatusLabel = computed(() => {
  if (copyStatus.value === 'copied') return t('feedback.copied')
  if (copyStatus.value === 'failed') return t('feedback.copyFailed')
  return ''
})
const commandActions = computed<Array<{ id: CommandId; label: string; hint: string; disabled: boolean }>>(() => {
  const actions = [
    {
      id: 'run' as const,
      label: t('command.runCurrent'),
      hint: currentToolTitle.value,
      disabled: runState.value === 'running' || runState.value === 'queued'
    },
    {
      id: 'copy' as const,
      label: t('command.copyResult'),
      hint: hasOutput.value ? `${outputBytes.value} B` : t('command.noResult'),
      disabled: !hasOutput.value
    },
    {
      id: 'theme' as const,
      label: t('command.toggleTheme'),
      hint: themeStatusLabel.value,
      disabled: false
    },
    {
      id: 'style' as const,
      label: t('command.toggleStyle'),
      hint: styleStatusLabel.value,
      disabled: false
    },
    {
      id: 'help' as const,
      label: t('command.openHelp'),
      hint: currentToolTitle.value,
      disabled: false
    },
    {
      id: 'refresh-status' as const,
      label: t('command.refreshStatus'),
      hint: systemStatusLabel.value,
      disabled: systemBusy.value
    }
  ]
  const query = commandQuery.value.trim().toLowerCase()
  if (!query) return actions
  return actions.filter((action) =>
    [action.label, action.hint, action.id].join(' ').toLowerCase().includes(query)
  )
})
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
  applyThemePreference(themePreference.value)
  applyStylePreference(stylePreference.value)
  window.addEventListener('keydown', handleGlobalKeydown)
  window.addEventListener('click', handleWindowClick)
  void loadAccount()
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  window.removeEventListener('click', handleWindowClick)
})

watch(themePreference, (next) => {
  applyThemePreference(next)
})

watch(stylePreference, (next) => {
  applyStylePreference(next)
})

function readStoredTheme(): ThemePreference {
  if (typeof window === 'undefined') return 'system'

  try {
    const stored = window.localStorage.getItem('yukit.theme')
    return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
  } catch {
    return 'system'
  }
}

function readStoredStyle(): StylePreference {
  if (typeof window === 'undefined') return 'default'

  try {
    return window.localStorage.getItem('yukit.style') === 'island' ? 'island' : 'default'
  } catch {
    return 'default'
  }
}

function applyThemePreference(preference: ThemePreference) {
  if (typeof document === 'undefined') return

  const resolved =
    preference === 'system'
      ? window.matchMedia?.('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : preference
  document.documentElement.dataset.theme = resolved
  document.documentElement.dataset.themePreference = preference

  try {
    window.localStorage.setItem('yukit.theme', preference)
  } catch {
    // Theme changes should still work when storage is blocked.
  }
}

function applyStylePreference(preference: StylePreference) {
  if (typeof document === 'undefined') return

  document.documentElement.dataset.style = preference

  try {
    window.localStorage.setItem('yukit.style', preference)
  } catch {
    // Style switching should keep working when storage is blocked.
  }
}

function cycleTheme() {
  themePreference.value = nextTheme(themePreference.value)
}

function cycleStyle() {
  stylePreference.value = nextStylePreference(stylePreference.value)
}

function selectLabel(value: string | number, choices: CustomSelectOption[]) {
  return choices.find((choice) => choice.value === value)?.label ?? String(value)
}

function toggleCustomSelect(selectId: SelectId) {
  openSelect.value = openSelect.value === selectId ? null : selectId
}

function closeCustomSelect() {
  openSelect.value = null
}

function handleWindowClick(event: MouseEvent) {
  const target = event.target instanceof Element ? event.target : null
  if (!target?.closest('.custom-select')) {
    closeCustomSelect()
  }
}

function isToolName(value: string): value is ToolName {
  return toolNames.includes(value as ToolName)
}

function openCommandMenu() {
  commandOpen.value = true
  helpOpen.value = false
  void nextTick(() => commandInput.value?.focus())
}

function closeOverlays() {
  commandOpen.value = false
  helpOpen.value = false
  authDialogOpen.value = false
  closeCustomSelect()
}

function handleGlobalKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    openCommandMenu()
    return
  }

  if (event.key === 'Escape' && openSelect.value) {
    event.preventDefault()
    closeCustomSelect()
    return
  }

  if (event.key === 'Escape' && (commandOpen.value || helpOpen.value || authDialogOpen.value)) {
    event.preventDefault()
    closeOverlays()
  }
}

function executeFirstCommand() {
  if (commandToolResults.value[0]) {
    selectTool(commandToolResults.value[0].name, commandToolResults.value[0].enabled)
    closeOverlays()
    return
  }

  const firstAction = commandActions.value.find((action) => !action.disabled)
  if (firstAction) {
    void executeCommand(firstAction.id)
  }
}

async function executeCommand(commandId: CommandId) {
  if (commandId === 'run') {
    closeOverlays()
    await runTool()
  } else if (commandId === 'copy') {
    closeOverlays()
    await copyOutput()
  } else if (commandId === 'theme') {
    cycleTheme()
  } else if (commandId === 'style') {
    cycleStyle()
  } else if (commandId === 'help') {
    commandOpen.value = false
    helpOpen.value = true
  } else {
    await refreshSystemStatus()
  }
}

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

async function loadAuthOptions() {
  if (authLoaded.value) return
  try {
    authOptions.value = await fetchAuthOptions()
    authLoaded.value = true
  } catch {
    authOptions.value = { dev_login: false, github: false, email: false }
    authError.value = t('auth.optionsUnavailable')
  }
}

async function openAuthDialog() {
  authDialogOpen.value = true
  commandOpen.value = false
  helpOpen.value = false
  authError.value = ''
  await loadAuthOptions()
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
  await openAuthDialog()
}

async function signInWithDev() {
  authBusy.value = true
  authError.value = ''
  try {
    currentUser.value = await devLogin()
    await loadUserResources()
    authDialogOpen.value = false
  } catch (error) {
    authError.value = error instanceof Error ? error.message : t('auth.signInFailed')
  } finally {
    authBusy.value = false
  }
}

function signInWithGitHub() {
  authError.value = ''
  window.location.href = `${apiBaseUrl()}/auth/github/start`
}

async function signOut() {
  authBusy.value = true
  authError.value = ''
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
  copyStatus.value = 'idle'
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
    await openAuthDialog()
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
  closeCustomSelect()
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
  try {
    await writeClipboard(output.value)
    copyStatus.value = 'copied'
  } catch {
    copyStatus.value = 'failed'
  }
  window.setTimeout(() => {
    copyStatus.value = 'idle'
  }, 1800)
}

async function writeClipboard(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', 'true')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  const copied = document.execCommand('copy')
  document.body.removeChild(textarea)
  if (!copied) {
    throw new Error('Copy failed')
  }
}

async function refreshSystemStatus() {
  systemBusy.value = true
  systemStatus.value = 'checking'
  try {
    const response = await fetch(`${apiBaseUrl()}/health`, { credentials: 'include' })
    if (!response.ok) throw new Error('Health check failed')
    systemStatus.value = 'healthy'
  } catch {
    systemStatus.value = 'unavailable'
  } finally {
    systemBusy.value = false
  }
}

function restoreExecution(item: ExecutionSummary) {
  if (isToolName(item.tool)) {
    selectedTool.value = item.tool
  }
  runState.value = isTerminalExecutionStatus(item.status) ? (item.status as RunState) : 'succeeded'
  durationMs.value = item.duration_ms
  output.value = serializeExecutionResult(item.result)
  errorMessage.value = item.error_message || item.error_code || ''
  activeTab.value = errorMessage.value && !output.value ? 'error' : 'raw'
  copyStatus.value = 'idle'
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand" aria-label="YuKit">
        <span class="brand-mark">Y</span>
        <span>YuKit</span>
      </div>
      <button
        class="command-search"
        type="button"
        aria-haspopup="dialog"
        :aria-expanded="commandOpen"
        @click="openCommandMenu"
      >
        <span>{{ t('toolbar.search') }}</span>
        <kbd>Ctrl K</kbd>
      </button>
      <div class="top-actions">
        <button
          class="style-toggle"
          :class="{ active: stylePreference === 'island' }"
          type="button"
          :title="styleButtonTitle"
          :aria-label="styleButtonTitle"
          @click="cycleStyle"
        >
          <span class="style-toggle-icon" aria-hidden="true"></span>
          <span>{{ styleStatusLabel }}</span>
        </button>
        <button
          class="language-toggle"
          type="button"
          :title="t('toolbar.languageButtonTitle')"
          :aria-label="t('toolbar.languageButtonTitle')"
          @click="toggleLocale"
        >
          {{ t('toolbar.languageSwitch') }}
        </button>
        <button
          class="icon-button"
          type="button"
          :title="t('toolbar.help')"
          :aria-label="t('toolbar.help')"
          @click="helpOpen = true"
        >
          ?
        </button>
        <button
          class="icon-button"
          type="button"
          :title="themeButtonTitle"
          :aria-label="themeButtonTitle"
          @click="cycleTheme"
        >
          ◐
        </button>
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

    <div v-if="commandOpen" class="overlay-backdrop" @click.self="closeOverlays">
      <section class="command-dialog" role="dialog" aria-modal="true" :aria-label="t('command.title')">
        <header class="dialog-head">
          <div>
            <strong>{{ t('command.title') }}</strong>
            <span>{{ t('command.subtitle') }}</span>
          </div>
          <button class="icon-button" type="button" :aria-label="t('actions.close')" @click="closeOverlays">
            ×
          </button>
        </header>

        <input
          ref="commandInput"
          v-model="commandQuery"
          class="command-input"
          type="search"
          :placeholder="t('command.placeholder')"
          @keydown.enter.prevent="executeFirstCommand"
        />

        <div class="command-section">
          <span class="section-label">{{ t('command.tools') }}</span>
          <button
            v-for="tool in commandToolResults"
            :key="tool.name"
            class="command-row"
            type="button"
            @click="selectTool(tool.name, tool.enabled); closeOverlays()"
          >
            <span class="tool-glyph">{{ tool.glyph }}</span>
            <span>
              <strong>{{ tool.title }}</strong>
              <small>{{ tool.meta }}</small>
            </span>
          </button>
          <p v-if="commandToolResults.length === 0" class="empty-copy">
            {{ t('command.noTools') }}
          </p>
        </div>

        <div class="command-section">
          <span class="section-label">{{ t('command.actions') }}</span>
          <button
            v-for="action in commandActions"
            :key="action.id"
            class="command-row"
            type="button"
            :disabled="action.disabled"
            @click="executeCommand(action.id)"
          >
            <span class="command-dot"></span>
            <span>
              <strong>{{ action.label }}</strong>
              <small>{{ action.hint }}</small>
            </span>
          </button>
        </div>
      </section>
    </div>

    <div v-if="helpOpen" class="overlay-backdrop" @click.self="closeOverlays">
      <section class="help-dialog" role="dialog" aria-modal="true" :aria-label="t('help.title')">
        <header class="dialog-head">
          <div>
            <strong>{{ t('help.title') }}</strong>
            <span>{{ currentToolTitle }}</span>
          </div>
          <button class="icon-button" type="button" :aria-label="t('actions.close')" @click="closeOverlays">
            ×
          </button>
        </header>
        <div class="help-body">
          <p>{{ currentToolDescription }}</p>
          <div class="help-grid">
            <span>{{ t('help.access') }}</span>
            <strong>{{ currentAccessBadge }}</strong>
            <span>{{ t('help.mode') }}</span>
            <strong>{{ currentModeBadge }}</strong>
            <span>{{ t('help.history') }}</span>
            <strong>{{ t('badges.inputNotStored') }}</strong>
            <span>{{ t('help.activeTool') }}</span>
            <strong>{{ currentTool?.title ?? currentToolTitle }}</strong>
          </div>
          <p class="empty-copy">{{ t('help.keyboard') }}</p>
        </div>
      </section>
    </div>

    <div v-if="authDialogOpen" class="overlay-backdrop" @click.self="closeOverlays">
      <section class="auth-dialog" role="dialog" aria-modal="true" :aria-label="t('auth.dialogTitle')">
        <header class="dialog-head">
          <div>
            <strong>{{ t('auth.dialogTitle') }}</strong>
            <span>{{ isSignedIn ? displayName : t('auth.dialogSubtitle') }}</span>
          </div>
          <button class="icon-button" type="button" :aria-label="t('actions.close')" @click="closeOverlays">
            ×
          </button>
        </header>

        <div class="auth-body">
          <div v-if="isSignedIn" class="auth-state">
            <strong>{{ t('auth.signedInAs') }}</strong>
            <span>{{ displayName }}</span>
            <button class="secondary-button" type="button" :disabled="authBusy" @click="signOut">
              {{ t('auth.signOut') }}
            </button>
          </div>

          <template v-else>
            <button
              v-if="authOptions.dev_login"
              class="auth-provider primary-button"
              type="button"
              :disabled="authBusy"
              @click="signInWithDev"
            >
              {{ authBusy && preferredAuthMethod === 'dev' ? t('auth.signingIn') : t('auth.localDevLogin') }}
            </button>

            <button
              v-if="authOptions.github"
              class="auth-provider secondary-button"
              type="button"
              :disabled="authBusy"
              @click="signInWithGitHub"
            >
              {{ t('auth.githubLogin') }}
            </button>

            <button
              v-if="!authOptions.github"
              class="auth-provider secondary-button"
              type="button"
              disabled
            >
              {{ t('auth.githubUnavailable') }}
            </button>

            <p v-if="preferredAuthMethod === 'none'" class="auth-warning">
              {{ t('auth.noProvider') }}
            </p>

            <p class="empty-copy">{{ t('auth.emailReserved') }}</p>
          </template>

          <p v-if="authError" class="auth-error">{{ authError }}</p>
        </div>
      </section>
    </div>

    <aside class="sidebar">
      <section>
        <div class="section-label">{{ t('sections.discover') }}</div>
        <div class="chips">
          <button
            v-for="tag in tagOptions"
            :key="tag.value"
            class="chip"
    :class="{ active: activeTag === tag.value }"
            type="button"
            @click="activeTag = tag.value"
          >
            {{ t(tag.labelKey) }}
          </button>
        </div>
      </section>

      <section>
        <div class="section-label">{{ t('sections.favorites') }}</div>
        <button v-if="!isSignedIn" class="sidebar-hint" type="button" @click="signIn">
          {{ t('favorites.signInHint') }}
        </button>
        <p v-else-if="favoriteToolItems.length === 0" class="empty-copy">
          {{ t('favorites.empty') }}
        </p>
        <div v-else class="favorite-list">
          <button
            v-for="tool in favoriteToolItems"
            :key="tool.name"
            class="favorite-item"
            type="button"
            @click="selectTool(tool.name, tool.enabled)"
          >
            <span class="tool-glyph">{{ tool.glyph }}</span>
            <span>{{ tool.title }}</span>
          </button>
        </div>
      </section>

      <nav class="tool-list" :aria-label="t('aria.tools')">
        <button
          v-for="tool in visibleTools"
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
        <p v-if="visibleTools.length === 0" class="empty-copy">
          {{ t('tools.noMatches') }}
        </p>
      </nav>

      <button
        class="system-badge"
        :class="systemTone"
        type="button"
        :disabled="systemBusy"
        @click="refreshSystemStatus"
      >
        {{ systemStatusLabel }}
      </button>
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
        <span v-if="copyStatusLabel" class="feedback-text">{{ copyStatusLabel }}</span>
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
              <div class="custom-select" @click.stop>
                <button
                  class="custom-select-trigger"
                  :class="{ open: openSelect === 'indent' }"
                  type="button"
                  aria-haspopup="listbox"
                  :aria-expanded="openSelect === 'indent'"
                  :aria-label="`${t('options.indentSize')} ${selectLabel(options.indent, indentChoices)}`"
                  @click="toggleCustomSelect('indent')"
                >
                  <span>{{ selectLabel(options.indent, indentChoices) }}</span>
                  <span class="custom-select-arrow" aria-hidden="true"></span>
                </button>
                <div v-if="openSelect === 'indent'" class="custom-select-menu" role="listbox">
                  <button
                    v-for="choice in indentChoices"
                    :key="choice.value"
                    class="custom-select-option"
                    :class="{ active: options.indent === choice.value }"
                    type="button"
                    role="option"
                    :aria-selected="options.indent === choice.value"
                    @click="options.indent = Number(choice.value); closeCustomSelect()"
                  >
                    {{ choice.label }}
                  </button>
                </div>
              </div>
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
              <div class="custom-select" @click.stop>
                <button
                  class="custom-select-trigger"
                  :class="{ open: openSelect === 'codec-mode' }"
                  type="button"
                  aria-haspopup="listbox"
                  :aria-expanded="openSelect === 'codec-mode'"
                  :aria-label="`${t('options.codecMode')} ${selectLabel(base64Options.mode, base64ModeChoices)}`"
                  @click="toggleCustomSelect('codec-mode')"
                >
                  <span>{{ selectLabel(base64Options.mode, base64ModeChoices) }}</span>
                  <span class="custom-select-arrow" aria-hidden="true"></span>
                </button>
                <div v-if="openSelect === 'codec-mode'" class="custom-select-menu" role="listbox">
                  <button
                    v-for="choice in base64ModeChoices"
                    :key="choice.value"
                    class="custom-select-option"
                    :class="{ active: base64Options.mode === choice.value }"
                    type="button"
                    role="option"
                    :aria-selected="base64Options.mode === choice.value"
                    @click="base64Options.mode = choice.value as Base64RunOptions['mode']; closeCustomSelect()"
                  >
                    {{ choice.label }}
                  </button>
                </div>
              </div>
            </label>

            <label class="field">
              <span>{{ t('options.charset') }}</span>
              <div class="custom-select" @click.stop>
                <button
                  class="custom-select-trigger"
                  :class="{ open: openSelect === 'charset' }"
                  type="button"
                  aria-haspopup="listbox"
                  :aria-expanded="openSelect === 'charset'"
                  :aria-label="`${t('options.charset')} ${selectLabel(base64Options.charset, charsetChoices)}`"
                  @click="toggleCustomSelect('charset')"
                >
                  <span>{{ selectLabel(base64Options.charset, charsetChoices) }}</span>
                  <span class="custom-select-arrow" aria-hidden="true"></span>
                </button>
                <div v-if="openSelect === 'charset'" class="custom-select-menu" role="listbox">
                  <button
                    v-for="choice in charsetChoices"
                    :key="choice.value"
                    class="custom-select-option"
                    :class="{ active: base64Options.charset === choice.value }"
                    type="button"
                    role="option"
                    :aria-selected="base64Options.charset === choice.value"
                    @click="base64Options.charset = choice.value as Base64RunOptions['charset']; closeCustomSelect()"
                  >
                    {{ choice.label }}
                  </button>
                </div>
              </div>
            </label>
            </template>

            <template v-else-if="selectedTool === 'timestamp'">
            <label class="field">
              <span>{{ t('options.timestampMode') }}</span>
              <div class="custom-select" @click.stop>
                <button
                  class="custom-select-trigger"
                  :class="{ open: openSelect === 'timestamp-mode' }"
                  type="button"
                  aria-haspopup="listbox"
                  :aria-expanded="openSelect === 'timestamp-mode'"
                  :aria-label="`${t('options.timestampMode')} ${selectLabel(timestampOptions.mode, timestampModeChoices)}`"
                  @click="toggleCustomSelect('timestamp-mode')"
                >
                  <span>{{ selectLabel(timestampOptions.mode, timestampModeChoices) }}</span>
                  <span class="custom-select-arrow" aria-hidden="true"></span>
                </button>
                <div v-if="openSelect === 'timestamp-mode'" class="custom-select-menu" role="listbox">
                  <button
                    v-for="choice in timestampModeChoices"
                    :key="choice.value"
                    class="custom-select-option"
                    :class="{ active: timestampOptions.mode === choice.value }"
                    type="button"
                    role="option"
                    :aria-selected="timestampOptions.mode === choice.value"
                    @click="timestampOptions.mode = choice.value as TimestampRunOptions['mode']; useSampleInput(); closeCustomSelect()"
                  >
                    {{ choice.label }}
                  </button>
                </div>
              </div>
            </label>
            </template>

            <template v-else-if="selectedTool === 'text-hash'">
            <label class="field">
              <span>{{ t('options.hashAlgorithm') }}</span>
              <div class="custom-select" @click.stop>
                <button
                  class="custom-select-trigger"
                  :class="{ open: openSelect === 'hash-algorithm' }"
                  type="button"
                  aria-haspopup="listbox"
                  :aria-expanded="openSelect === 'hash-algorithm'"
                  :aria-label="`${t('options.hashAlgorithm')} ${selectLabel(textHashOptions.algorithm, hashAlgorithmChoices)}`"
                  @click="toggleCustomSelect('hash-algorithm')"
                >
                  <span>{{ selectLabel(textHashOptions.algorithm, hashAlgorithmChoices) }}</span>
                  <span class="custom-select-arrow" aria-hidden="true"></span>
                </button>
                <div v-if="openSelect === 'hash-algorithm'" class="custom-select-menu" role="listbox">
                  <button
                    v-for="choice in hashAlgorithmChoices"
                    :key="choice.value"
                    class="custom-select-option"
                    :class="{ active: textHashOptions.algorithm === choice.value }"
                    type="button"
                    role="option"
                    :aria-selected="textHashOptions.algorithm === choice.value"
                    @click="textHashOptions.algorithm = choice.value as TextHashRunOptions['algorithm']; closeCustomSelect()"
                  >
                    {{ choice.label }}
                  </button>
                </div>
              </div>
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
              <div class="custom-select" @click.stop>
                <button
                  class="custom-select-trigger"
                  :class="{ open: openSelect === 'regex-timeout' }"
                  type="button"
                  aria-haspopup="listbox"
                  :aria-expanded="openSelect === 'regex-timeout'"
                  :aria-label="`${t('options.timeoutMs')} ${selectLabel(regexOptions.timeoutMs, regexTimeoutChoices)}`"
                  @click="toggleCustomSelect('regex-timeout')"
                >
                  <span>{{ selectLabel(regexOptions.timeoutMs, regexTimeoutChoices) }}</span>
                  <span class="custom-select-arrow" aria-hidden="true"></span>
                </button>
                <div v-if="openSelect === 'regex-timeout'" class="custom-select-menu" role="listbox">
                  <button
                    v-for="choice in regexTimeoutChoices"
                    :key="choice.value"
                    class="custom-select-option"
                    :class="{ active: regexOptions.timeoutMs === choice.value }"
                    type="button"
                    role="option"
                    :aria-selected="regexOptions.timeoutMs === choice.value"
                    @click="regexOptions.timeoutMs = Number(choice.value); closeCustomSelect()"
                  >
                    {{ choice.label }}
                  </button>
                </div>
              </div>
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
                @click="restoreExecution(item)"
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
