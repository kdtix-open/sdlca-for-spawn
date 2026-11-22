// SPDX-License-Identifier: Apache-2.0
// Save one screenshot of a joined body's page.
// usage: bun lib/shot.mjs <cdp-url> <out.png> [wait-seconds] [yaw|-] [pitch|-] [session]
// With a yaw or pitch it first aims the camera (see aim() below); the session names the body for `spawn client where`.
// Exit status: 0 a picture was saved; 3 the page was too busy to answer in time (try again); anything else, it failed.
// The page is the Chromium tab that `spawn client join --render cpu` prints; Playwright attaches to it
// over the Chrome DevTools Protocol. Only local endpoints are accepted.
// It writes the picture wherever it is told. bin/sdlca-look gives it a path in a private folder of its own and
// places the file at the caller's path afterwards, as a new file that never follows a link, and it does not show
// the "saved" line below, because that path is the private one.
import { chromium } from 'playwright-core'
import { execFileSync } from 'node:child_process'

const [, , cdp, out, wait = '8', yawArg = '-', pitchArg = '-', session = ''] = process.argv
if (!cdp || !out) {
  console.error('usage: shot.mjs <cdp-url> <out.png> [wait-seconds]')
  process.exit(2)
}
const host = new URL(cdp).hostname
if (host !== '127.0.0.1' && host !== 'localhost') {
  console.error('refusing a CDP endpoint that is not on this machine')
  process.exit(2)
}

const wrap = (d) => ((((d + 180) % 360) + 360) % 360) - 180
// The look as the game's own sim reports it (a documented verb), or null.
function readLook() {
  try {
    const text = execFileSync('spawn', ['client', 'where', '--name', session], { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'ignore'] })
    const m = /look: yaw (-?\d+)\D+pitch (-?\d+)/.exec(text)
    return m ? { yaw: Number(m[1]), pitch: Number(m[2]) } : null
  } catch {
    return null
  }
}
// Aim like a player: the first click takes the pointer lock, and under it a mouse move turns the look. How far a pixel turns it is not
// assumed: one small move measures it for each axis, then a few corrections close the gap. Best effort: a picture is taken either way.
async function aim(page, wantYaw, wantPitch) {
  let size = page.viewportSize()
  if (!size) size = await page.evaluate(() => ({ width: innerWidth, height: innerHeight }))
  let x = size.width / 2, y = size.height / 2
  await page.mouse.move(x, y)
  await page.mouse.click(x, y)
  await page.waitForTimeout(500)
  let look = readLook()
  if (!look) return console.error('shot.mjs: could not read the look; the camera was not aimed')
  const gain = { yaw: 0, pitch: 0 }
  const nudge = async (axis, px) => {
    const before = look
    const nx = axis === 'yaw' ? Math.min(Math.max(x + px, 10), size.width - 10) : x
    const ny = axis === 'pitch' ? Math.min(Math.max(y + px, 10), size.height - 10) : y
    const moved = axis === 'yaw' ? nx - x : ny - y
    if (moved === 0) return false
    for (let i = 1; i <= 8; i++) await page.mouse.move(x + ((nx - x) * i) / 8, y + ((ny - y) * i) / 8)
    x = nx
    y = ny
    await page.waitForTimeout(400)
    look = readLook() || before
    const turned = axis === 'yaw' ? wrap(look.yaw - before.yaw) : look.pitch - before.pitch
    if (Math.abs(turned) >= 1) gain[axis] = turned / moved
    return true
  }
  for (let round = 0; round < 6; round++) {
    const errYaw = wantYaw === null ? 0 : wrap(wantYaw - look.yaw)
    const errPitch = wantPitch === null ? 0 : wantPitch - look.pitch
    if (Math.abs(errYaw) <= 3 && Math.abs(errPitch) <= 3) break
    console.error('shot.mjs: aim round ' + round + ': yaw ' + look.yaw + ' pitch ' + look.pitch + ', gains ' + gain.yaw.toFixed(3) + ' ' + gain.pitch.toFixed(3) + ', mouse at ' + Math.round(x) + ',' + Math.round(y))
    if (Math.abs(errYaw) > 3) await nudge('yaw', gain.yaw ? Math.max(-300, Math.min(300, Math.round(errYaw / gain.yaw))) : 30)
    if (Math.abs(errPitch) > 3) await nudge('pitch', gain.pitch ? Math.max(-200, Math.min(200, Math.round(errPitch / gain.pitch))) : 30)
  }
  console.error('shot.mjs: look is now yaw ' + look.yaw + ' pitch ' + look.pitch)
}

const browser = await chromium.connectOverCDP(cdp)
try {
  const page = browser.contexts()[0].pages()[0]
  // The software renderer draws nothing until the world has loaded, so early pictures are black. bin/sdlca-look decides whether a
  // picture is real, and calls this again until it is; this only waits as long as it is told and takes one picture.
  await page.waitForTimeout(Number(wait) * 1000)
  if ((yawArg !== '-' || pitchArg !== '-') && session) await aim(page, yawArg === '-' ? null : wrap(Number(yawArg)), pitchArg === '-' ? null : Number(pitchArg))
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
