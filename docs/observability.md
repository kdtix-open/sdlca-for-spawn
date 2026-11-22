# Observability: finding out where a turn spent its time

This page is for the person who runs the SDLCA agent kit and wants to know why an agent's turn was slow, or what it did while it was quiet. The kit writes a small trace of every turn, and `sdlca-trace` turns it into a timeline with hints. Everything here ran against real turns on 2026-11-22 unless the page says otherwise.

## The first finding, so you know what this is for

A simple "check the text on the plate and fix it" turn took about 12 minutes. The agent's own session file showed where it went:

| Turn | Wall time | Inside `sdlca-look` | Model and every other tool |
| --- | --- | --- | --- |
| The slow card turn | 676 s | 624 s (5 looks, 176 to 267 s each) | 41 s |
| An earlier turn with one look | 203 s | 172 s | 22 s |
| A turn with no look | 30 s | none | 30 s |

So 94% of the slow turn was waiting for looks, and each look pays for a cold join of the world and for the software renderer to draw it. Editing a file took 0.1 s. Chat took 4 to 8 s a reply, and most of that is a deliberate 2.2-second pause between lines, because Spawn rate-limits chat.

## What is recorded

One line of JSON per event, in `~/.sdlca/spawn/accounts/<account>/trace.jsonl` (the file starts again at 4 MB, and the old one is kept as `trace.jsonl.1`). Each line has `ts` (milliseconds since 1970), `turn` (the id of the turn, which the handler hands to the agent's tools as `SDLCA_TURN_ID`), `ev` (what happened) and the facts for that event.

| Event | Written by | Facts |
| --- | --- | --- |
| `turn.start`, `turn.end` | the handler | kind of event, world, sender handle, event id; total time and status |
| `lock.acquired` | the handler | `wait_ms`: how long the turn queued for the world's lock |
| `refresh` | the handler | `dur_ms`, `status`: the clone update before the agent runs |
| `agent.start`, `agent.end` | the handler | `dur_ms`, `rc` (124 or 137 means it ran out of time) |
| `look.start`, `look.join`, `look.shot`, `look.end` | `sdlca-look` | render, size, the two points; join time; each picture attempt (`dur_ms`, `rc`, `bytes`); the whole look |
| `shot.wait`, `shot.place`, `shot.aim`, `shot.screenshot` | the screenshot tool | the waiting, placing, aiming and picture steps, and where the body ended |
| `say.line`, `say.total` | `sdlca-say` | each chat line's time; lines, total time and the deliberate pauses |
| `api.call` | `sdlca-api` | method, path without its query, time, status |
| `asset.upload` | `sdlca-asset` | time, status, bytes |

Never in the file: chat text, a token, a file's contents. A value that is not a whole number is cut to 200 characters and every character outside letters, digits and `. _ : @ / -` and space becomes an underscore. `SDLCA_TRACE=0` in the account's `env` turns the trace off. Tracing never fails the thing it watches.

## Reading it

```bash
bin/sdlca-trace lanthief                  # the last 5 turns, with hints
bin/sdlca-trace lanthief --last 20 --json # one JSON object per turn, for a script
bin/sdlca-trace lanthief --turn t1700000000000-4242
bin/sdlca-trace lanthief --transcripts    # adds the agent's own steps, from Claude Code's session files
```

A turn looks like this (the numbers are from a test, not from your machine):

```
turn t1700000000000-100   2023-11-14 22:13:20   chat_mention @alice/game-1
  total 180.5 s: lock wait 15.0 s, clone update 0.8 s, agent 179.0 s (status 0)
    look (whole)                         1 x   158.0 s  (88% of the agent's time)
      look: join the world               1 x    17.0 s
      look: picture attempts             2 x   140.0 s
    chat (sdlca-say)                     1 x     7.8 s  (4% of the agent's time)
    pictures: 2 attempts, 1 blank, 0 failed
  hint: looks are 88% of the agent's time (1 look). ...
```

The hints are rules of thumb that say where to look: looks taking most of the time, more than one look in a turn, blank pictures, a long wait for the world's lock, a slow clone update, the chat pause, an agent that ran out of time.

`--transcripts` reads Claude Code's own session files (`~/.claude/projects`, or the folder in `SDLCA_AGENT_TRANSCRIPTS`), finds the session that overlaps the turn, and adds the time inside each tool and the time left for the model. It reads only timestamps and tool names, and prints nothing from the conversation. It only works when the agent command is Claude Code.

## A root-cause routine

1. `sdlca-trace <account>`. Is the time in the lock wait, the clone update, the agent, or after it?
2. If it is the agent, the span lines say which tool. Add `--transcripts` to see the model's own share.
3. If it is a look, the sub-lines say which part: the join, a wait for the world to draw, placing or aiming. More than one blank picture means the first wait was too short.
4. Change one thing, run the same ask again, and compare the two turns.

## Not built yet (planned)

- A body that stays in the world (a resident eye), so that a look is a screenshot and not a cold join. This is the largest saving the numbers above point at.
- A state-change log for a world's own board (a card's status over time) next to the kit's trace.
- Counting the agent's model calls and tokens per turn.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
