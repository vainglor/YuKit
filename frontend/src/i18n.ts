import { ref } from 'vue'

const STORAGE_KEY = 'yukit.locale'

export const locales = ['en', 'zh-CN'] as const
export type Locale = (typeof locales)[number]

const en = {
  'actions.clear': 'Clear',
  'actions.copyResult': 'Copy result',
  'actions.favorite': 'Favorite',
  'actions.reset': 'Reset',
  'actions.run': 'Run',
  'actions.running': 'Running',
  'actions.sample': 'Sample',
  'aria.executionStatus': 'Execution status',
  'aria.jsonInput': 'JSON input',
  'aria.tools': 'Tools',
  'auth.signIn': 'Sign in',
  'badges.inputNotStored': 'Input not stored',
  'badges.public': 'Public',
  'badges.sync': 'Sync',
  'errors.noLatestError': 'No error for the latest run.',
  'errors.sanitized': 'Errors are sanitized by the API and do not expose stack traces.',
  'errors.unexpectedToolRunFailure': 'Unexpected tool run failure',
  'options.compact': 'Compact',
  'options.ensureAscii': 'Ensure ASCII',
  'options.ensureAsciiHelp': 'Escape non-ASCII characters when needed.',
  'options.historyPolicy': 'History policy',
  'options.historyPolicyHelp': 'Save run metadata only. Raw input is omitted unless a tool opts in.',
  'options.indentSize': 'Indent size',
  'options.noSavedRuns': 'No saved runs yet.',
  'options.recentRuns': 'Recent runs',
  'options.sortKeys': 'Sort keys',
  'options.sortKeysHelp': 'Alphabetize object keys for stable diffs.',
  'options.spaces2': '2 spaces',
  'options.spaces4': '4 spaces',
  'options.spaces8': '8 spaces',
  'panels.input': 'Input',
  'panels.options': 'Options',
  'panels.output': 'Output',
  'placeholders.rawOutput': 'Run the tool to see formatted JSON.',
  'placeholders.treeOutput': 'Tree view appears after a successful run.',
  'sections.discover': 'Discover',
  'sections.favorites': 'Favorites',
  'status.failed': 'Failed',
  'status.ready': 'Ready',
  'status.running': 'Running',
  'status.succeeded': 'Succeeded',
  'system.healthy': 'System healthy',
  'tabs.error': 'Error',
  'tabs.raw': 'Raw',
  'tabs.tree': 'Tree',
  'tags.all': 'All',
  'tags.codec': 'Codec',
  'tags.format': 'Format',
  'tags.text': 'Text',
  'tags.time': 'Time',
  'toolbar.help': 'Help',
  'toolbar.languageButtonTitle': 'Switch language',
  'toolbar.languageSwitch': '中文',
  'toolbar.search': 'Search tools or press command menu',
  'toolbar.theme': 'Theme',
  'tools.base64.meta': 'Planned',
  'tools.base64.title': 'Base64',
  'tools.jsonFormat.meta': 'Public · Sync',
  'tools.jsonFormat.title': 'JSON Format',
  'tools.regex.meta': 'Planned',
  'tools.regex.title': 'Regex Test',
  'tools.timestamp.meta': 'Planned',
  'tools.timestamp.title': 'Timestamp',
  'workspace.description': 'Validate, format, and normalize JSON. Inputs stay local to the run history policy.',
  'workspace.kicker': 'Developer · Format',
  'workspace.title': 'JSON Format'
} as const

type MessageKey = keyof typeof en

const zh: Record<MessageKey, string> = {
  'actions.clear': '清空',
  'actions.copyResult': '复制结果',
  'actions.favorite': '收藏',
  'actions.reset': '重置',
  'actions.run': '运行',
  'actions.running': '运行中',
  'actions.sample': '示例',
  'aria.executionStatus': '执行状态',
  'aria.jsonInput': 'JSON 输入',
  'aria.tools': '工具',
  'auth.signIn': '登录',
  'badges.inputNotStored': '不保存输入',
  'badges.public': '公开',
  'badges.sync': '同步',
  'errors.noLatestError': '最近一次运行没有错误。',
  'errors.sanitized': '错误信息已由 API 处理，不会暴露堆栈。',
  'errors.unexpectedToolRunFailure': '工具运行失败',
  'options.compact': '紧凑',
  'options.ensureAscii': '确保 ASCII',
  'options.ensureAsciiHelp': '需要时转义非 ASCII 字符。',
  'options.historyPolicy': '历史策略',
  'options.historyPolicyHelp': '仅保存运行元数据。除非工具明确开启，否则不会保存原始输入。',
  'options.indentSize': '缩进大小',
  'options.noSavedRuns': '还没有保存的运行记录。',
  'options.recentRuns': '最近运行',
  'options.sortKeys': '键名排序',
  'options.sortKeysHelp': '按字母顺序排列对象键，方便稳定对比。',
  'options.spaces2': '2 个空格',
  'options.spaces4': '4 个空格',
  'options.spaces8': '8 个空格',
  'panels.input': '输入',
  'panels.options': '选项',
  'panels.output': '输出',
  'placeholders.rawOutput': '运行工具后查看格式化 JSON。',
  'placeholders.treeOutput': '成功运行后显示树形视图。',
  'sections.discover': '发现',
  'sections.favorites': '收藏',
  'status.failed': '失败',
  'status.ready': '就绪',
  'status.running': '运行中',
  'status.succeeded': '成功',
  'system.healthy': '系统正常',
  'tabs.error': '错误',
  'tabs.raw': '原始',
  'tabs.tree': '树形',
  'tags.all': '全部',
  'tags.codec': '编解码',
  'tags.format': '格式化',
  'tags.text': '文本',
  'tags.time': '时间',
  'toolbar.help': '帮助',
  'toolbar.languageButtonTitle': '切换语言',
  'toolbar.languageSwitch': 'EN',
  'toolbar.search': '搜索工具或打开命令菜单',
  'toolbar.theme': '主题',
  'tools.base64.meta': '规划中',
  'tools.base64.title': 'Base64',
  'tools.jsonFormat.meta': '公开 · 同步',
  'tools.jsonFormat.title': 'JSON 格式化',
  'tools.regex.meta': '规划中',
  'tools.regex.title': '正则测试',
  'tools.timestamp.meta': '规划中',
  'tools.timestamp.title': '时间戳',
  'workspace.description': '校验、格式化并规范化 JSON。输入遵循运行历史策略。',
  'workspace.kicker': '开发者 · 格式化',
  'workspace.title': 'JSON 格式化'
}

const messages: Record<Locale, Record<MessageKey, string>> = {
  en,
  'zh-CN': zh
}

function isLocale(value: string | null): value is Locale {
  return locales.includes(value as Locale)
}

function readStoredLocale(): Locale {
  if (typeof window === 'undefined') return 'en'

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return isLocale(stored) ? stored : 'en'
  } catch {
    return 'en'
  }
}

function applyLocale(locale: Locale) {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }

  if (typeof window !== 'undefined') {
    try {
      window.localStorage.setItem(STORAGE_KEY, locale)
    } catch {
      // Ignore blocked storage; language switching should still work in memory.
    }
  }
}

export const currentLocale = ref<Locale>(readStoredLocale())

applyLocale(currentLocale.value)

export function setLocale(locale: Locale) {
  currentLocale.value = locale
  applyLocale(locale)
}

export function toggleLocale() {
  setLocale(currentLocale.value === 'en' ? 'zh-CN' : 'en')
}

export function t(key: MessageKey | string): string {
  const activeMessages = messages[currentLocale.value] as Record<string, string>
  const fallbackMessages = messages.en as Record<string, string>
  return activeMessages[key] ?? fallbackMessages[key] ?? key
}
