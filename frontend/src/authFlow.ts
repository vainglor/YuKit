export type AuthOptions = {
  dev_login: boolean
  github: boolean
  email: boolean
}

export type LoginMethod = 'dev' | 'github' | 'none'

export function normalizeAuthOptions(value: Partial<AuthOptions> | null | undefined): AuthOptions {
  return {
    dev_login: Boolean(value?.dev_login),
    github: Boolean(value?.github),
    email: Boolean(value?.email)
  }
}

export function preferredLoginMethod(options: AuthOptions): LoginMethod {
  if (options.dev_login) return 'dev'
  if (options.github) return 'github'
  return 'none'
}
