// SPDX-License-Identifier: Apache-2.0
// Save one screenshot of a joined body's page.
// usage: bun lib/shot.mjs <cdp-url> <out.png> [wait-seconds] [yaw|-] [pitch|-] [session] [at|-] [face|-]
// at and face are 'x,y,z' in world metres: the body is stood there (a transient game script run, see place() below) and the camera is
// turned toward the face point from the eye (feet + 1.6 m). Yaw 0 faces -z (forward is (-sin yaw, -cos yaw)); positive pitch looks up.
// With a yaw or pitch it first aims the camera (see aim() below); the session names the body for `spawn client where`.
// Exit status: 0 a picture was saved; 3 the page was too busy to answer in time (try again); anything else, it failed.
// The page is the Chromium tab that `spawn client join --render cpu` prints; Playwright attaches to it
// over the Chrome DevTools Protocol. Only local endpoints are accepted.
// It writes the picture wherever it is told. bin/sdlca-look gives it a path in a private folder of its own and
// places the file at the caller's path afterwards, as a new file that never follows a link, and it does not show
// the "saved" line below, because that path is the private one.
import { chromium } from 'playwright-core'
import { execFileSync } from 'node:child_process'

const [, , cdp, out, wait = '8', yawArg = '-', pitchArg = '-', session = '', atArg = '-', faceArg = '-'] = process.argv
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
  // A mouse move can only go as far as the page is wide, and under the pointer lock a move is all the turn there is: about 170 degrees from
  // one edge to the other. The click that takes the lock turns nothing, so it is made at the edge the turn starts from (moving right turns
  // the look to lower yaw, as in a game), and the whole width is then there to turn through.
  const first = readLook()
  let x = size.width / 2, y = size.height / 2
  if (first && wantYaw !== null && Math.abs(wrap(wantYaw - first.yaw)) > 25) x = wrap(wantYaw - first.yaw) < 0 ? 10 : size.width - 10
  if (first && wantPitch !== null && Math.abs(wantPitch - first.pitch) > 25) y = wantPitch - first.pitch < 0 ? size.height - 10 : 10
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
    const steps = Math.max(8, Math.ceil(Math.abs(moved) / 40))
    for (let i = 1; i <= steps; i++) await page.mouse.move(x + ((nx - x) * i) / steps, y + ((ny - y) * i) / steps)
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
    if (Math.abs(errYaw) > 3) await nudge('yaw', gain.yaw ? Math.max(-1300, Math.min(1300, Math.round(errYaw / gain.yaw))) : errYaw < 0 ? 30 : -30)
    if (Math.abs(errPitch) > 3) await nudge('pitch', gain.pitch ? Math.max(-700, Math.min(700, Math.round(errPitch / gain.pitch))) : errPitch > 0 ? -30 : 30)
  }
  console.error('shot.mjs: look is now yaw ' + look.yaw + ' pitch ' + look.pitch)
}

const EYE = 1.6
const point = (text) => text.split(',').map(Number)
// The body's position as the game's own sim reports it, or null.
function readPosition() {
  try {
    const text = execFileSync('spawn', ['client', 'where', '--name', session], { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'ignore'] })
    const m = /position: \((-?[\d.]+), (-?[\d.]+), (-?[\d.]+)\)/.exec(text)
    return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null
  } catch {
    return null
  }
}
// Stand the body's feet at a world position. It is a run of the client's `exec` in the game realm without --persist, so nothing is
// saved: the body moves in this room and the world's files are untouched. A world can move a body again while it arrives (a hold that
// keeps it on the floor), so the position is read back and the move is repeated a few times. Returns the position reached, or null.
async function place(target) {
  const [x, y, z] = target
  const source = 'ctx.self.feetPosition = { x: ' + x + ', y: ' + y + ', z: ' + z + ' }; return 1;'
  let got = readPosition()
  if (got && Math.hypot(got[0] - x, got[2] - z) < 0.5 && Math.abs(got[1] - y) < 0.5) return got // already there (an earlier call of this tool placed it)
  for (let attempt = 0; attempt < 5; attempt++) {
    try {
      execFileSync('spawn', ['client', 'exec', '--name', session, '-e', source], { encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'ignore', 'ignore'] })
    } catch {
      console.error('shot.mjs: the placement run failed (attempt ' + (attempt + 1) + ')')
    }
    await new Promise((resolve) => setTimeout(resolve, 1500)) // not page.waitForTimeout: the page can be replaced while the body is placed
    got = readPosition()
    if (got && Math.hypot(got[0] - x, got[2] - z) < 0.5 && Math.abs(got[1] - y) < 0.5) break
  }
  console.error('shot.mjs: body wanted at ' + target.join(', ') + ', now at ' + (got ? got.map((v) => v.toFixed(2)).join(', ') : 'unknown'))
  return got
}
// The yaw and pitch (degrees) that turn the camera from an eye toward a point. Forward is (-sin yaw, -cos yaw).
function lookAngles(eye, target) {
  const dx = target[0] - eye[0], dy = target[1] - eye[1], dz = target[2] - eye[2]
  const flat = Math.hypot(dx, dz)
  if (flat < 1e-6 && Math.abs(dy) < 1e-6) return null
  return { yaw: Math.round((Math.atan2(-dx, -dz) * 180) / Math.PI), pitch: Math.round((Math.atan2(dy, flat) * 180) / Math.PI) }
}

const browser = await chromium.connectOverCDP(cdp)
try {
  let page = browser.contexts()[0].pages()[0]
  // The software renderer draws nothing until the world has loaded, so early pictures are black. bin/sdlca-look decides whether a
  // picture is real, and calls this again until it is; this only waits as long as it is told and takes one picture.
  await page.waitForTimeout(Number(wait) * 1000)
  let wantYaw = yawArg === '-' ? null : wrap(Number(yawArg))
  let wantPitch = pitchArg === '-' ? null : Number(pitchArg)
  let feet = null
  if (atArg !== '-' && session) {
    feet = await place(point(atArg))
    page = browser.contexts()[0].pages()[0] // the page may have been replaced by the move
  }
  if (faceArg !== '-' && session) {
    feet = feet || readPosition()
    if (!feet) console.error('shot.mjs: could not read where the body stands; --face was not used')
    else {
      const angles = lookAngles([feet[0], feet[1] + EYE, feet[2]], point(faceArg))
      if (angles) {
        if (wantYaw === null) wantYaw = angles.yaw
        if (wantPitch === null) wantPitch = Math.max(-80, Math.min(80, angles.pitch))
      }
    }
  }
  if ((wantYaw !== null || wantPitch !== null) && session) await aim(page, wantYaw, wantPitch)
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
