// SPDX-License-Identifier: Apache-2.0
// Save one screenshot of a joined body's page.
// usage: bun lib/shot.mjs <cdp-url> <out.png> [wait-seconds]
// Exit status: 0 a picture was saved; 3 the page was too busy to answer in time (try again); anything else, it failed.
// The page is the Chromium tab that `spawn client join --render cpu` prints; Playwright attaches to it
// over the Chrome DevTools Protocol. Only local endpoints are accepted.
// It writes the picture wherever it is told. bin/sdlca-look gives it a path in a private folder of its own and
// places the file at the caller's path afterwards, as a new file that never follows a link, and it does not show
// the "saved" line below, because that path is the private one.
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
  // The software renderer draws nothing until the world has loaded, so early pictures are black. bin/sdlca-look decides whether a
  // picture is real, and calls this again until it is; this only waits as long as it is told and takes one picture.
  await page.waitForTimeout(Number(wait) * 1000)
  await page.screenshot({ path: out })
  console.log('saved', out)
} catch (error) {
  // While the world loads, the page is too busy drawing to answer: the screenshot times out. That is not a failure of this tool, and
  // bin/sdlca-look asks again, so it gets a status of its own (3) and one plain line, not a stack trace.
  if (error && error.name === 'TimeoutError') {
    console.error('shot.mjs: the page did not answer in time; it is busy drawing')
    process.exitCode = 3
  } else {
    throw error
  }
} finally {
  await browser.close() // lets go of the page; the body stays in the world until `spawn client leave`
}
