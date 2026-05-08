import { beforeEach, describe, expect, it } from 'vitest'

import { currentLocale, setLocale, t, toggleLocale } from './i18n'

describe('i18n', () => {
  beforeEach(() => {
    setLocale('en')
  })

  it('translates labels for the active locale', () => {
    expect(currentLocale.value).toBe('en')
    expect(t('actions.run')).toBe('Run')

    setLocale('zh-CN')

    expect(currentLocale.value).toBe('zh-CN')
    expect(t('actions.run')).toBe('运行')
    expect(t('toolbar.languageSwitch')).toBe('EN')
  })

  it('toggles between English and Chinese', () => {
    toggleLocale()
    expect(currentLocale.value).toBe('zh-CN')
    expect(t('toolbar.search')).toBe('搜索工具或打开命令菜单')

    toggleLocale()
    expect(currentLocale.value).toBe('en')
    expect(t('toolbar.search')).toBe('Search tools or press command menu')
  })

  it('falls back to the key when a translation is missing', () => {
    expect(t('missing.translation')).toBe('missing.translation')
  })
})
