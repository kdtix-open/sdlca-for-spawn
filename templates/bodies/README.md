# The body that ships with the kit

`kdtix-agent-body.glb` is a rigged 3D body that an agent can wear in a Spawn world: a silver humanoid robot with the KDTIX open-source gear mark on its chest. It is the only model file in this repository.

## Where it came from, and what was decided

- On 2026-11-19, Spawn's character sculpt made it from a KDTIX picture: the KDTIX robot with the open-source gear mark, which KDTIX made. A person ran the kit's `sdlca-body` for an agent of theirs and the sculpt took about four minutes.
- On 2026-11-20 a maintainer decided to ship this one file with the kit. The picture is KDTIX's own, and its mark says that the project is for the community.
- **No other generated model is shipped** until the maintainers have reviewed the question further. A test, `tests/test_shipped_body.py`, fails if another model file is added.
- Spawn was not asked whether its terms allow this file to be kept here.

## What is inside the file

| What | Value |
| --- | --- |
| Size | 5,246,192 bytes |
| SHA-256 | `c05edacaa1275c9acb8e93f0875eb6e92e8b49748740e66735b464c5636d8fe0` |
| Format | glTF binary, version 2, compressed with meshopt and KTX2 textures |
| Skeleton | One skin of 54 joints |
| Animation clips | Six: `Idle`, `Walk`, `Run`, `Sprint`, `Jump` and one named `Armature\|clip0\|baselayer` |
| Generator tag | glTF-Transform 4.3.0, an open-source tool |
| Extra data | A few lines of Spawn's own processing notes under `asset.extras.spawn` |

The skeleton, the five named animation clips and the processing notes come from Spawn's pipeline, not from the picture. Their terms have not been reviewed, and that is part of the further review that the decision above waits for.

## License

The maintainers have not given this file a license of its own. Treat it like the rest of this repository (Apache-2.0). That license grants no right in the KDTIX name or mark (section 6 of the license), and it does not cover anything of Spawn's that is inside the file.

## How to use it

Today it works as a body for one join, not as the agent's own profile body. Carry it once from an agent that is an editor of a world, and the address is always the same, because it is named by the file's hash:

```bash
bin/sdlca-body alice --carry templates/bodies/kdtix-agent-body.glb --world @alice/game-1 --apply
bin/sdlca-as alice spawn client join @alice/game-1 --body https://www.spawn.co/cdn/value.c05edacaa1275c9acb8e93f0875eb6e92e8b49748740e66735b464c5636d8fe0.glb --ttl 600
```

Do not paste what the join prints, because it can hold a credential. In our test on 2026-11-20, Spawn refused the same address as an agent's profile body with `body_not_carried`, so `sdlca-body --wear` does not work with it yet. [Giving an agent a body](../../docs/giving-an-agent-a-body.md) tells the whole story, including how to make a profile body with a sculpt of the agent's own.
