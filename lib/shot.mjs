// SPDX-License-Identifier: Apache-2.0
// Save one screenshot of a joined body's page.
// usage: bun lib/shot.mjs <cdp-url> <out.png> [wait-seconds]
// The page is the Chromium tab that `spawn client join --render cpu` prints; Playwright attaches to it
// over the Chrome DevTools Protocol. Only local endpoints are accepted.
import { chromium } from 'playwright-core'

const [, , cdp, out, wait = '8'] = process.argv
if (!cdp || !out) {
  console.error('usage: shot.mjs <cdp-url> <out.png> [wait-seconds]')
  process.exit(2)
}
const host = new URL(cdp).hostname
if (host !== '127.0.0.1' && host !== 'localhost') {
  console.error('refusing a CDP endpoint that is not on this machine')
  process.exit(2)
}

const browser = await chromium.connectOverCDP(cdp)
try {
  const page = browser.contexts()[0].pages()[0]
  // The software renderer needs a few seconds before the first real frame (the very first is black).
  await page.waitForTimeout(Number(wait) * 1000)
  await page.screenshot({ path: out })
  console.log('saved', out)
} finally {
  await browser.close() // lets go of the page; the body stays in the world until `spawn client leave`
}
