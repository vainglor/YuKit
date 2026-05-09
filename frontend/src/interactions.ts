export type ThemePreference = 'light' | 'dark' | 'system'
export type ToolTag = 'all' | 'format' | 'codec' | 'time' | 'text'

export type ToolCatalogItem = {
  name: string
  title: string
  meta: string
  tags: readonly Exclude<ToolTag, 'all'>[]
}

export function filterTools<Tool extends ToolCatalogItem>(
  tools: Tool[],
  query: string,
  activeTag: ToolTag
): Tool[] {
  const normalizedQuery = query.trim().toLowerCase()

  return tools.filter((tool) => {
    const tagMatches = activeTag === 'all' || tool.tags.includes(activeTag)
    if (!tagMatches) return false

    if (!normalizedQuery) return true

    const searchable = [tool.name, tool.title, tool.meta, ...tool.tags].join(' ').toLowerCase()
    return searchable.includes(normalizedQuery)
  })
}

export function nextTheme(current: ThemePreference): ThemePreference {
  if (current === 'light') return 'dark'
  if (current === 'dark') return 'system'
  return 'light'
}

export function serializeExecutionResult(result: unknown): string {
  if (result === null || result === undefined) return ''
  if (typeof result === 'string') return result
  if (typeof result === 'number' || typeof result === 'boolean' || typeof result === 'bigint') {
    return String(result)
  }
  return JSON.stringify(result, null, 2)
}
