# Technical Breakdown — CaptainBigButt Proportion Trick

A deep dive into how the tool works, what files it produces, and why the math eliminates the need for Blender.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Idea](#the-idea)
- [Where the Data Comes From](#where-the-data-comes-from)
- [Bone Matching](#bone-matching)
- [Building the Two SMDs](#building-the-two-smds)
  - [The Shared-Rotation Trick](#the-shared-rotation-trick)
  - [Axis Conversion](#axis-conversion)
  - [SMD File Format](#smd-file-format)
- [The QC Snippet](#the-qc-snippet)
  - [subtract → Pure Position Delta](#subtract--pure-position-delta)
  - [delta autoplay](#delta-autoplay)
  - [The Ragdoll Sequence](#the-ragdoll-sequence)
  - [IK Chains](#ik-chains)
- [Why Blender Isn't Needed](#why-blender-isnt-needed)
- [Edge Cases and Limits](#edge-cases-and-limits)

---

## The Problem

Garry's Mod plays **HL2 female skeleton animations** on every playermodel. These animations encode movement as bone positions and rotations relative to the HL2 female reference pose.

When a custom playermodel has **different bone lengths** (longer arms, shorter legs, wider torso, etc.), the HL2 animations still move bones by the HL2 distances. The result: limbs stretch, clip, float, or compress because the engine blindly applies HL2 positional offsets to a skeleton they were never designed for.

The **proportion trick** (originally documented by [CaptainBigButt](https://steamcommunity.com/sharedfiles/filedetails/?id=2308084980)) fixes this by encoding the positional difference between the two skeletons as a **delta animation** that plays on top of everything else, shifting each bone from where HL2 *thinks* it should be to where the model's skeleton *actually* puts it.

## The Idea

Generate two single-frame animations that share **identical rotations** but have **different positions**:

| File | Positions | Rotations |
|---|---|---|
| `proportions.smd` | Model's bone positions | Model's bone rotations |
| `hl2_female_reference.smd` | HL2 female bone positions | Model's bone rotations |

Then use studiomdl's `subtract` command:

```
$animation a_proportions "proportions.smd" subtract hl2_ref 0
```

Because the rotations match exactly, the subtraction zeroes them out. What remains is a **pure position delta** — the vector from each HL2 bone position to the corresponding model bone position.

When this delta is applied as an `autoplay` sequence, every frame of every animation gets quietly corrected. Bones land where the model's skeleton intended, not where the HL2 skeleton assumed.

## Where the Data Comes From

Everything the tool needs is already sitting in the model's decompiled **QC file**, specifically the `$definebone` lines. These look like:

```qc
$definebone "ValveBiped.Bip01_Pelvis" "" -0.000005 -0.78846 37.913784  0 0 89.999982
$definebone "ValveBiped.Bip01_Spine" "ValveBiped.Bip01_Pelvis" 0.000005 4.212788 -1.689857  -1.602964 89.999982 89.999982
```

Each line defines:
- **Bone name** — e.g. `ValveBiped.Bip01_Pelvis`
- **Parent name** — empty string for root bones
- **Position** (X, Y, Z) — bone's offset from its parent, in Source engine units
- **Rotation** (X, Y, Z) — bone's rest-pose orientation in **degrees**

The tool parses these with a regex:
```python
_DEFINEBONE_RE = re.compile(
    r'\$definebone\s+'
    r'"([^"]+)"\s+'                                      # bone name
    r'"([^"]*)"\s+'                                      # parent name
    r'([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+'   # pos X Y Z
    r'([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',      # rot X Y Z (degrees)
    re.IGNORECASE,
)
```

The HL2 female reference skeleton is **embedded** in the tool as a block of `$definebone` text (parsed with the same function), so there's nothing external to download.

## Bone Matching

Not every bone in a model matters to the proportion trick. The tool maintains a list of **53 core ValveBiped bones** — the ones that HL2 animations actually drive:

- Pelvis, Spine (×4), Neck, Head
- Left/Right: Clavicle, UpperArm, Forearm, Hand
- Left/Right: Finger0–4 with two child joints each
- Left/Right: Thigh, Calf, Foot, Toe

Any bone **not** in this list is a "custom bone" — jigglebones, physics helpers, attachment points, flex controllers, etc. These are **excluded** from the SMDs entirely.

The matching logic:

1. Walk the model's `$definebone` entries
2. For each, check if the name exists in the 53-bone ValveBiped set (case-insensitive)
3. Only matched bones appear in the output SMDs

Custom bones aren't affected by the proportion trick and don't need correction — they're defined relative to their parent, which *does* get corrected, so they follow along.

### Parent Hierarchy

The HL2 reference skeleton may have bones between two matched bones that the model doesn't have (or vice versa). To build the SMD's `nodes` section (which requires a flat parent-index reference), the tool walks **up** the HL2 hierarchy from each bone until it finds the nearest parent that's also in the matched set:

```python
def find_parent_idx(bone_name):
    parent = ref_bones[bone_name]['parent']
    while parent:
        if parent in matched_set:
            return name_to_idx[parent]
        parent = ref_bones.get(parent, {}).get('parent')
    return -1  # root
```

This ensures the SMD's bone tree is self-consistent even when intermediate bones are skipped.

## Building the Two SMDs

### The Shared-Rotation Trick

This is the key insight that makes the whole method work.

Both SMDs use the **model's** rotation values. Only the positions differ:

```python
# For each matched bone:
proportions_data.append(
    (bone_name, pid, list(model_bone['position']), list(smd_rot))
)
hl2_ref_data.append(
    (bone_name, pid, list(ref_bone['position']),   list(smd_rot))
)
```

`model_bone['position']` and `ref_bone['position']` come from two different `$definebone` sets, but `smd_rot` is always from the **model**. This guarantees that when studiomdl subtracts one from the other, the rotational component is exactly zero.

### Axis Conversion

`$definebone` stores rotations as **(X, Y, Z) in degrees**. SMD stores rotations as **(Z, X, Y) in radians** (Euler order differs). The tool converts:

```python
r = model_bone['rotation_rad']     # [X, Y, Z] already in radians
smd_rot = [r[2], r[0], r[1]]      # reorder to [Z, X, Y]
```

Since both SMDs go through the same conversion, the reordering is consistent and the subtraction still zeroes out.

### SMD File Format

The generated SMDs are minimal, skeleton-only, single-frame animation files:

```
version 1
nodes
  0 "ValveBiped.Bip01_Pelvis" -1
  1 "ValveBiped.Bip01_Spine" 0
  2 "ValveBiped.Bip01_Spine1" 1
  ...
end
skeleton
time 0
  0  -0.000005 -0.788460 37.913784  1.570796 0.000000 0.000000
  1   0.000005  4.212788 -1.689857  1.570796 -0.027973 1.570796
  ...
end
```

**`nodes`** — Lists every bone with a zero-based index, quoted name, and parent index (-1 = root).

**`skeleton`** — A single keyframe at `time 0`. Each bone line has: index, position X Y Z, rotation Z X Y (radians).

There is no triangle/mesh data. These files exist purely to carry skeleton poses into studiomdl's `subtract` math.

## The QC Snippet

The tool generates a text file (`corrective_qc_snippet.txt`) meant to be pasted into the model's QC file after the `$sequence "reference"` line:

```qc
$sequence hl2_ref "anims/hl2_female_reference.smd" fps 1 hidden

$animation a_proportions "anims/proportions.smd" subtract hl2_ref 0

$sequence proportions a_proportions delta autoplay
```

Each line has a specific role.

### subtract → Pure Position Delta

```qc
$animation a_proportions "anims/proportions.smd" subtract hl2_ref 0
```

`subtract hl2_ref 0` tells studiomdl: *"Take every bone in `proportions.smd` and subtract the corresponding bone's values from frame 0 of `hl2_ref`."*

For positions: `delta_pos = model_pos - hl2_pos`
For rotations: `delta_rot = model_rot - model_rot = 0`

The result (`a_proportions`) is a single-frame animation containing only positional offsets.

### delta autoplay

```qc
$sequence proportions a_proportions delta autoplay
```

- **`delta`** — This animation is additive. Instead of replacing bone transforms, it adds its values on top of whatever's already playing.
- **`autoplay`** — The engine plays this sequence automatically on every frame, on every model instance. No Lua code needed.

Combined: every animation frame gets the positional correction applied transparently.

### The Ragdoll Sequence

```qc
$Sequence "ragdoll" {
    "anims/hl2_female_reference.smd"
    activity "ACT_DIERAGDOLL" 1
    fadein 0.2
    fadeout 0.2
    fps 30
}
```

Source engine requires a sequence tagged with `ACT_DIERAGDOLL` for ragdoll physics to work. If the model doesn't already have one, this provides it using the HL2 reference as a rest pose. Without it, killing a player may produce no ragdoll or a T-pose corpse.

### IK Chains

If the tool detects `$ikchain` entries in the original QC (common for feet and hands), it adds comments reminding the modder to keep their `$ikchain` / `$ikautoplaylock` definitions **above** the proportion snippet. IK locks ensure feet stay planted on the ground and don't float after the positional correction is applied.

## Why Blender Isn't Needed

Older approaches to proportion correction required importing the model into Blender, posing bones, exporting SMDs, and running studiomdl — a multi-tool pipeline that broke whenever Blender's Source Tools changed or the user had a different Blender version.

This tool skips all of that because:

1. **`$definebone` contains everything.** Bone names, hierarchy, positions, and rotations are all in the QC text. No 3D geometry is involved.
2. **No mesh data is needed.** The SMDs are skeleton-only — no vertices, no triangles, no UV maps. Writing them is string formatting, not 3D math.
3. **The rotations are copied, not computed.** There's no need to solve inverse kinematics, transform matrices, or quaternion math. The model's rotations go into both SMDs verbatim (after axis reordering).
4. **studiomdl does the hard part.** The actual subtraction and delta application happen inside Valve's compiler. The tool just prepares the inputs.

The entire pipeline is: **parse text → write text → let studiomdl compile**.

## Edge Cases and Limits

| Scenario | Behavior |
|---|---|
| **Model has >128 total bones** | Only ~53 matched ValveBiped bones go into the SMDs — well under the limit. The full model may need special handling (see README's high bone count workflow). |
| **Model has no ValveBiped bones** | Tool reports "no matching bones" and stops. The model uses a non-standard skeleton that HL2 animations don't target. |
| **Model has extra non-ValveBiped bones** | Ignored. Jigglebones, attachment points, and physics bones aren't in the proportion SMDs. They inherit correction from their corrected parents. |
| **Bone names differ in case** | Matching is case-insensitive. `valvebiped.bip01_pelvis` matches `ValveBiped.Bip01_Pelvis`. |
| **Model is already HL2 female proportions** | The delta will be near-zero for all bones. Harmless — compiles fine, just has no visible effect. |
| **QC has $ikchain** | Tool adds IK-related comments to the snippet. User must ensure `$ikchain` / `$ikautoplaylock` are defined before the snippet. |

---

*Method credit: [CaptainBigButt](https://steamcommunity.com/sharedfiles/filedetails/?id=2308084980) — Tool: [Link2738](https://github.com/Link2738)*
