# Giving an agent a body: day zero and day n+1

This page is for someone who runs the SDLCA agent kit and wants their agent to have a body of its own, instead of Spawn's default one. It tells two stories about `sdlca-body`, the command that does it. The first is day zero, the day you give an agent its first body. The second is day n+1, every day after that: undoing the body, finishing a sculpt that was interrupted, replacing it, and sharing it with a second agent. The examples use the owner `alice`, whose kit account is also called `alice` and whose agent is `@@alice_helper`. Replace the names with yours.

Everything here was run against the real Spawn on 2026-11-19 or 2026-11-20, unless the page says that a step ran only against a stand-in or has not been tried. The reference text for each option is the header of `bin/sdlca-body` (run `bin/sdlca-body --help`), and [Operations](operations.md#giving-an-agent-a-body) has the short version. The kit is unofficial and Spawn did not review this page.

## Before day zero

You need three things.

- **An agent account that is linked to a person.** The kit makes one with `sdlca-onboard` ([Getting started](getting-started.md)). The person it is linked to pays for the sculpt, which is why an agent that no person is linked to cannot make a body.
- **A picture of the body.** A PNG, JPEG or WebP of at most 4 MB, showing the whole body, that you have the right to upload. Spawn reviews it like any other upload, [Spawn's terms](compliance/spawn-rules.md) apply to you, and the body is shown to everyone who sees the agent in a world.
- **A way to keep what the tool prints.** The sculpt's id and the character's id appear once, and they are what you need to undo or resume later. The tool prints no token and no secret, so it is safe to keep a log: add `2>&1 | tee -a ~/alice-body.log` to a command.

You do not need a world, a browser or Spawn's client for the sculpt itself. You run `sdlca-body` yourself, from your own shell. It is not for the agent: it spends the person's money, and it refuses to run inside an agent turn ([why](security-model.md#why-an-agent-must-not-run-sdlca-body)).

## Day zero: alice gives her agent its first body

### 1. Look first

Run the command with only the account and the picture. Without `--apply` it changes nothing and only reads from Spawn.

```bash
bin/sdlca-body alice ~/Pictures/agent-body.png
```

It prints a plan: who the agent is, who pays, what it wears now, and what the picture is (its type, its size, a fingerprint, and any text, camera data or extra bytes it carries, which would be sent along). It ends with `This was a dry run`. Read three lines before you go on:

- `linked to: alice (generation is open)` means that Spawn will make a body for this agent. If it says the generation lane is closed, the words after it are Spawn's, and the agent needs a person who is linked to it.
- `paid by: @alice` is the person whose allowance pays for the sculpt.
- `wears now: Spawn's default body` means that the agent has no body of its own yet.

### 2. Do it

Add `--apply`.

```bash
bin/sdlca-body alice ~/Pictures/agent-body.png --apply 2>&1 | tee -a ~/alice-body.log
```

The tool prints the plan again and then works through four steps. Each one is a call to a door that Spawn publishes:

1. `uploading the picture` and then `uploaded as a draft (character ..., picture ...)`. Spawn has reviewed the picture and kept it as a draft.
2. `starting the sculpt (the linked person pays for this step)` and then `started: job ...`. This is the step that is paid for. The tool prints, right here, the command that carries on if the run is stopped.
3. `waiting for the sculpt`, with a line each time Spawn reports a new stage. In our real run the stages were `preparing_image`, then `generating_3d`, then `finalizing`, and the sculpt was complete after 3 minutes 57 seconds.
4. `wearing the body`, then `checked: the agent's profile now names the body`, then `done: the body is worn`.

The last lines are the two you want to copy into your log: the command that takes the body off again (it has the character's id in it), and a note about sharing the body with another agent ([day n+1](#i-want-my-second-agent-to-look-the-same) tells that story).

### 3. Check

Run the first command again, the one without `--apply`. The plan now says `wears now: a body of its own (a new one replaces it)`. That line is the check, and it asks Spawn, so it does not rely on what the tool said a minute ago.

### 4. See it

A body is shown while the agent is in a world, and the kit's agent is in a world only while `sdlca-look` takes a screenshot. To look at the new body, open the world in your own browser while the agent stands in it. This puts the agent in the world for five minutes, and everyone in the room can see it:

```bash
bin/sdlca-as alice spawn client join @alice/game-1 --ttl 300 --render none
```

Do not paste what the join prints, because it can hold a credential. The body leaves by itself when the time is over, or sooner with `bin/sdlca-as alice spawn client leave`. We checked that the agent stands in the world with a body of its own. We have not looked at the result in a browser ourselves, so tell us if it looks wrong.

### Or use the body that ships with the kit

If you have no picture, or you only want to see how a body looks on your agent, the kit ships one: `templates/bodies/kdtix-agent-body.glb`, a silver robot with the KDTIX open-source gear mark. It is a finished model, so there is no sculpt and nothing to pay for. A maintainer decided on 2026-11-20 to ship it and no other generated model for now, and the folder's [README](../templates/bodies/README.md) says where it came from and what is inside it. Today it works as a body for one join, not as the agent's profile body (see [the second-agent story below](#i-want-my-second-agent-to-look-the-same)): carry it once, then join with it.

```bash
bin/sdlca-body alice --carry templates/bodies/kdtix-agent-body.glb --world @alice/game-1 --apply
bin/sdlca-as alice spawn client join @alice/game-1 --body https://www.spawn.co/cdn/value.c05edacaa1275c9acb8e93f0875eb6e92e8b49748740e66735b464c5636d8fe0.glb --ttl 600
```

### If the run stops before the end

Closing the terminal, pressing Ctrl-C, or a wait that runs out (15 minutes unless you pass `--wait`) does not lose the sculpt. It keeps running at Spawn. The tool prints a command of this form, and you run it:

```bash
bin/sdlca-body alice --job <the job id> --apply
```

That waits for the same sculpt and wears it. It makes nothing again, so it costs nothing. If you did not keep the id, see [a new picture run says that a sculpt is recorded](#a-new-picture-run-says-that-a-sculpt-is-recorded) below.

## Day n+1: keeping the body

### I want the default body back

Use the command that the tool printed when the body was worn. It has the character's id in it:

```bash
bin/sdlca-body alice --reset <the character id> --apply
```

Spawn answers that the reset went through, and a dry run then says `wears now: Spawn's default body`. We ran this for real on 2026-11-20.

### I changed my mind, and I want the sculpt back

A reset does not throw the sculpt away. The finished sculpt is still there, and you can wear it again without making a new one. Use the sculpt's id from your log:

```bash
bin/sdlca-body alice --job <the job id> --apply
```

We ran exactly this round trip on a real agent on 2026-11-20: reset to the default body, then wear the same finished sculpt again. It made no new sculpt, so there was no new charge, and the agent ended with the same body. This is also why the ids in your log are worth keeping.

### I want a different body

Run the picture command again with the new picture. A new body replaces the old one, and it is a new sculpt, so it is paid for again. The plan says `a new one replaces it` before you commit to it. You do not need to reset first.

### A new picture run says that a sculpt is recorded

This is on purpose. Just before the tool asks Spawn for a sculpt, it writes a small file, `body-sculpt.json`, in the account's folder (`~/.sdlca/spawn/accounts/alice/`). While that file exists, a picture run for the account refuses, so that a second paid sculpt cannot start by accident: by a second terminal, a lost screen, or a re-run after an unclear answer. The file is removed when the body is worn or the sculpt has failed. The message tells you what to do, and there are two cases:

- **It names a job.** Carry on with it: `bin/sdlca-body alice --job <that id> --apply`. If the job is finished or you gave up on it, delete the file and run the picture command again.
- **It says an earlier run may have started a sculpt that Spawn did not confirm.** The tool asked for a sculpt and the answer was lost or unclear (a dropped connection, a server error, Ctrl-C). Look at your characters on spawn.co. If one is being sculpted, let it finish. When you are sure that none is, or you accept a second one, delete the file and run the picture command again.

### I want my second agent to look the same

This is the part that does not work as well as we hoped, so here is exactly what we know. The sculpt is the costly step and happens once, so the question is how to put the same model on a second agent. We tried the road that Spawn's guide describes, on 2026-11-20, with the agents of two different people.

**What worked.** Carry the model file to Spawn once, and then any agent can stand in a world wearing it for one join.

```bash
# 1. get the model's file (the address is the one printed after the sculpt)
curl -L -o body.glb https://www.spawn.co/magic/character-robot-character-ABCD1234.glb
# 2. carry it to Spawn, from an agent that is an editor of a world; it prints the address to use
bin/sdlca-body bob --carry body.glb --world @bob/den --apply
# 3. the agent stands in a world wearing it, for one join
bin/sdlca-as bob spawn client join @bob/den --body https://www.spawn.co/cdn/value.<hash>.glb --ttl 600
```

Use the whole https address in step 3: the client does not take the short `/cdn/...` form. The carry is open to every agent account. A file over 4.4 MB goes by Spawn's road for large files (the tool does that for you, and the token never goes to the storage host). The dry run, without `--apply`, shows what the file is, whether it has a skeleton, and which world it would go through.

**What did not work.** Making that address the second agent's own body, the one on its profile:

```bash
bin/sdlca-body bob --wear https://www.spawn.co/cdn/value.<hash>.glb --apply
```

Spawn refused this with `body_not_carried`, both for the address printed after a sculpt and for an address that the carry printed. It refused it even though the same address worked for a join. Spawn's published description says the body must be "your own carried" file, and we have not found out what more it needs. One idea we have not tried is carrying through a world that the agent owns, which would mean making a world under the agent's handle. Until this is known, the way to give a second agent a profile body of its own is a sculpt of its own: run the picture command for that agent's account, and its person pays for it.

**What carrying leaves behind.** The file is stored with that world's assets, under a name that is its own hash. Anyone who knows the address can fetch it, and Spawn screens it. Carry only a file you may upload.

### Something did not go as planned

| What the tool says | What it means, and what to do |
| --- | --- |
| `this is not an agent account` | You named an account that holds a person's token. Use the agent's account. |
| `generation lane ... closed` | Spawn will not make a body for this agent. The words after it are Spawn's. |
| `Spawn did not accept the picture as a draft` | Spawn's review refused the picture, and nothing was sculpted. Try another picture. |
| `the sculpt did not finish` | Spawn could not make a body from that picture, and nothing was worn. Try another picture. |
| `Spawn may have started it anyway` | The answer to the request for the sculpt was lost or unclear. Look at your characters on spawn.co before you run anything again. |
| `body_not_carried` | Spawn did not take that address as the agent's own body. See [above](#i-want-my-second-agent-to-look-the-same). |
| `the wait ended` (exit status 3) | The sculpt is still running at Spawn. Run the `--job` command the tool printed. |
| `a sculpt is already recorded` | See [above](#a-new-picture-run-says-that-a-sculpt-is-recorded). |

### Housekeeping

- **Cost.** A sculpt is paid for by the person the agent is linked to. We cannot see the amount from the kit, so look at the person's usage on Spawn. Undoing a body, wearing a sculpt again, carrying a file and wearing a look make no sculpt.
- **What leaves your machine.** The picture goes to Spawn exactly as it is, under a fixed file name, so the name of your file and its folders are not sent. Text or camera data inside the picture goes with it, and so do any bytes after its end. The plan names both before anything is sent. The account's token goes only to Spawn.
- **What the tool keeps.** The one small file described above, only while a sculpt is recorded. It prints to your terminal and writes nothing else.
- **Upgrading the kit.** Nothing to migrate. A newer kit reads the same record file.

## Not built yet

These are planned, and the kit does not do them today.

- A face for the agent (Spawn lets an agent set a small picture of itself).
- A body that stays in a room, instead of appearing only while a screenshot is taken.
- Making a shared body the profile body of a second agent without a sculpt of its own, which needs Spawn to accept it, or a world that the agent owns.
- Listing the sculpts and characters that an agent already has. Today the ids come from your own log.

Unofficial community project, not affiliated with Spawn. Licensed under Apache-2.0.
