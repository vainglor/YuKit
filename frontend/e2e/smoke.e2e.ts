import { expect, test } from '@playwright/test'

test('renders the toolbox workspace', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: /JSON Format|JSON 格式化/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Run|运行/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Text Hash|文本哈希/ })).toBeVisible()
})

test('wires visible workspace controls', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ user: null })
    })
  })
  await page.route('**/api/auth/options', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ dev_login: true, github: false, email: false })
    })
  })

  await page.goto('/')

  await page.getByRole('button', { name: /Search tools|搜索工具/ }).click()
  await expect(page.getByRole('dialog', { name: /Command menu|命令菜单/ })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: /Command menu|命令菜单/ })).toBeHidden()

  await page.getByRole('button', { name: /Switch to light theme|切换到浅色主题/ }).click()
  await expect
    .poll(() => page.evaluate(() => document.documentElement.dataset.themePreference))
    .toBe('light')

  await page.getByRole('button', { name: /Codec|编解码/ }).click()
  const toolList = page.locator('.tool-list')
  await expect(toolList.getByRole('button', { name: /Base64/ })).toBeVisible()
  await expect(toolList.getByRole('button', { name: /JSON Format|JSON 格式化/ })).toBeHidden()

  await page.getByRole('button', { name: /^(Sign in|登录)$/ }).click()
  await expect(page.getByRole('dialog', { name: /^(Sign in|登录)$/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Continue as Local User|以本地用户继续/ })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: /^(Sign in|登录)$/ })).toBeHidden()
})
