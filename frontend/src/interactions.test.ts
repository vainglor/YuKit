import { describe, expect, it } from 'vitest'

import {
  filterTools,
  nextStylePreference,
  nextTheme,
  serializeExecutionResult,
  type ToolCatalogItem
} from './interactions'

const tools: ToolCatalogItem[] = [
  {
    name: 'json-format',
    title: 'JSON Format',
    meta: 'Developer · Format',
    tags: ['format']
  },
  {
    name: 'base64',
    title: 'Base64',
    meta: 'Developer · Codec',
    tags: ['codec']
  },
  {
    name: 'timestamp',
    title: 'Timestamp',
    meta: 'Developer · Time',
    tags: ['time']
  }
]

describe('filterTools', () => {
  it('filters tools by query across title, metadata, tags, and name', () => {
    expect(filterTools(tools, 'json', 'all').map((tool) => tool.name)).toEqual(['json-format'])
    expect(filterTools(tools, 'developer', 'all').map((tool) => tool.name)).toEqual([
      'json-format',
      'base64',
      'timestamp'
    ])
  })

  it('filters tools by active tag', () => {
    expect(filterTools(tools, '', 'codec').map((tool) => tool.name)).toEqual(['base64'])
  })

  it('combines query and tag filters', () => {
    expect(filterTools(tools, 'json', 'codec')).toEqual([])
  })
})

describe('nextTheme', () => {
  it('cycles light, dark, and system preferences', () => {
    expect(nextTheme('light')).toBe('dark')
    expect(nextTheme('dark')).toBe('system')
    expect(nextTheme('system')).toBe('light')
  })
})

describe('nextStylePreference', () => {
  it('toggles between default and island styles', () => {
    expect(nextStylePreference('default')).toBe('island')
    expect(nextStylePreference('island')).toBe('default')
  })
})

describe('serializeExecutionResult', () => {
  it('keeps string results readable', () => {
    expect(serializeExecutionResult('plain')).toBe('plain')
  })

  it('pretty prints structured results', () => {
    expect(serializeExecutionResult({ digest: 'abc' })).toBe('{\n  "digest": "abc"\n}')
  })

  it('handles empty results without showing undefined', () => {
    expect(serializeExecutionResult(null)).toBe('')
    expect(serializeExecutionResult(undefined)).toBe('')
  })
})
