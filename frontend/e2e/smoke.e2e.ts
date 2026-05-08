import { expect, test } from '@playwright/test'

test('renders the toolbox workspace', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: /JSON Format|JSON 格式化/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Run|运行/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /Text Hash|文本哈希/ })).toBeVisible()
})
