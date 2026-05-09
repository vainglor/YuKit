import { describe, expect, it } from 'vitest'

import { normalizeAuthOptions, preferredLoginMethod } from './authFlow'

describe('normalizeAuthOptions', () => {
  it('defaults missing auth options to false', () => {
    expect(normalizeAuthOptions({ dev_login: true })).toEqual({
      dev_login: true,
      github: false,
      email: false
    })
  })
})

describe('preferredLoginMethod', () => {
  it('prefers local dev login when available', () => {
    expect(preferredLoginMethod({ dev_login: true, github: true, email: false })).toBe('dev')
  })

  it('uses GitHub when dev login is unavailable', () => {
    expect(preferredLoginMethod({ dev_login: false, github: true, email: false })).toBe('github')
  })

  it('returns none when no implemented provider is available', () => {
    expect(preferredLoginMethod({ dev_login: false, github: false, email: false })).toBe('none')
  })
})
