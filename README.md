# GMod PM Proportion Tool

A standalone tool that generates **CaptainBigButt's Proportion Trick** files for Garry's Mod playermodels — no Blender required.

The proportion trick fixes the stretched/squished look custom playermodels get in GMod by applying a position-only delta that adjusts bone lengths to match the HL2 female skeleton (what GMod animations expect).

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: Unlicense](https://img.shields.io/badge/license-Unlicense-green)

## What It Does

1. Reads `$definebone` entries from your decompiled QC file
2. Generates two skeleton-only SMD animation files:
   - `proportions.smd` — your model's bone positions & rotations
   - `hl2_female_reference.smd` — HL2 female bone positions with your model's rotations
3. Outputs a ready-to-paste QC snippet that wires everything up

Because both files share identical rotations, studiomdl's `subtract` produces a **pure position delta** with zero rotation artifacts — no gimbal lock, no deformation issues.

The proportion trick files only contain the ~53 matched ValveBiped bones, so they work with any studiomdl compiler regardless of how many bones your full model has.

## How To Use

### 1. Decompile your model
Use [Crowbar](https://steamcommunity.com/groups/CrowbarTool) to decompile your playermodel. You need the `.qc` file with `$definebone` lines.

### 2. Run the tool
```
python app.py
```

- **Browse** to your decompiled `.qc` file
- The tool analyzes the skeleton and shows matched/custom bones
- Click **Generate Proportion Files**
- Click **Copy QC Snippet** to copy the snippet to your clipboard

### 3. Edit your QC
Paste the snippet into your QC file. Place it **after** any `$ikautoplaylock` lines and **before** `$includemodel`:

```qc
// ... your existing QC content ...

$ikautoplaylock rfoot 1 0
$ikautoplaylock lfoot 1 0

// ---- Proportion Trick (paste here) ----
$sequence "hl2_reference" {
    "mymodel_anims/hl2_female_reference.smd"
    hidden
    fps 1
}

$sequence "proportions" {
    "mymodel_anims/proportions.smd"
    hidden
    delta
    subtract "hl2_reference" 0
    autoplay
}
// ---- End Proportion Trick ----

$includemodel "f_anm.mdl"
```

### 4. Recompile
Compile with studiomdl (via Crowbar) and your model will have proper proportions in GMod.

> **Note:** If your full model has >128 bones and uses DMX mesh files, the proportion trick SMD files still work fine alongside them in the same QC — studiomdl handles mixed formats.

## High Bone Count Models (>128 bones, DMX workflow)

Models with more than 128 bones (e.g. anime models with hair/skirt/breast physics chains) cannot be compiled with GMod's SDK 2013 studiomdl — it has a 128-bone limit. You need **SFM's studiomdl** which supports up to 256 bones, and your mesh files need to be in **DMX format** (not SMD).

The proportion trick files themselves are always SMD and only contain ~53 bones, so they work fine. This guide covers getting everything else set up.

### Prerequisites

- [Crowbar 0.74+](https://steamcommunity.com/groups/CrowbarTool) — decompile & compile tool
- [Blender](https://www.blender.org/) — 3D editor for import/export
- [Blender Source Tools](https://developer.valvesoftware.com/wiki/Blender_Source_Tools) — Blender addon for Source engine formats
- [Source Filmmaker (SFM)](https://store.steampowered.com/app/1840/Source_Filmmaker/) — installed via Steam (provides the studiomdl that supports DMX)

### Step 1 — Decompile with Crowbar

1. Open **Crowbar** → **Decompile** tab
2. Select your `.mdl` file
3. Set output folder (e.g. `Desktop/testbed/crowbar_out/mymodel/`)
4. Click **Decompile**
5. You'll get a `.qc` file and `.smd` mesh/animation files

### Step 2 — Import into Blender & export as DMX

The SMD mesh files from Crowbar won't support >128 bones when recompiled. Convert them to DMX:

1. Open **Blender** with **Blender Source Tools** installed
2. **File → Import → Source Engine (.smd, .vta, .dmx, .qc)**
3. Select your `.qc` file — this imports the reference mesh and skeleton
4. Verify the import: check the armature has all bones, mesh looks correct
5. **File → Export → Source Engine (.smd, .vta, .dmx, .qc)**
6. Set format to **DMX** in export settings
7. Export to your working folder (e.g. `Desktop/testbed/blender/`)
8. BST exports individual body groups as separate `.dmx` files

> **Tip:** If your model has shape keys (flex controllers), they're baked into the DMX mesh automatically — no separate `.vta` file needed.

### Step 3 — Generate proportion trick files

1. Run this tool: `python app.py`
2. Browse to the **original decompiled QC** (from Crowbar, not Blender's export)
3. Click **Generate Proportion Files**
4. Copy the generated `anims/` folder (containing `proportions.smd` and `hl2_female_reference.smd`) into your Blender export folder

### Step 4 — Set up the QC

Your QC needs to reference the DMX mesh files and the SMD proportion files. The key points:

- `$model`/`$body` lines point to `.dmx` mesh files
- `$sequence`/`$animation` proportion trick lines point to `.smd` files
- If your original QC had `flexfile` blocks inside `$model { }`, **remove them** — DMX already contains shape keys internally
- studiomdl reads each source file independently by its header, so mixing `.dmx` and `.smd` in the same QC works fine

Example QC structure:
```qc
$modelname "player/mymodel.mdl"

// DMX mesh files (from Blender Source Tools export)
$model "body" "mymodel.dmx"
$model "arms" "arms.dmx"

$definebone "ValveBiped.Bip01_Pelvis" "" ...
// ... all $definebone lines ...

$ikchain "rhand" "ValveBiped.Bip01_R_Hand" ...
$ikchain "lhand" "ValveBiped.Bip01_L_Hand" ...
$ikchain "rfoot" "ValveBiped.Bip01_R_Foot" ...
$ikchain "lfoot" "ValveBiped.Bip01_L_Foot" ...

// Standard reference + idle (can be SMD or DMX)
$sequence "reference" "reference.smd" fps 1

// Proportion trick (always SMD — only ~53 bones)
$sequence hl2_ref "anims/hl2_female_reference.smd" fps 1 hidden
$animation a_proportions "anims/proportions.smd" subtract hl2_ref 0
$sequence proportions a_proportions delta autoplay

$sequence "ragdoll" {
    "anims/hl2_female_reference.smd"
    activity "ACT_DIERAGDOLL" 1
    fadein 0.2
    fadeout 0.2
    fps 30
}

$includemodel "f_anm.mdl"
$includemodel "m_anm.mdl"
```

### Step 5 — Compile with SFM's studiomdl

1. Open **Crowbar** → **Compile** tab
2. Select your QC file
3. **Important:** Set the game to **Source Filmmaker** (or manually point to SFM's studiomdl at `Steam/steamapps/common/SourceFilmmaker/game/bin/studiomdl.exe`)
4. Click **Compile**
5. The compiled `.mdl` goes to SFM's `usermod/models/` folder — copy it to your GMod `models/` folder

The compiled MDL works in GMod — SFM and GMod use the same MDL format (v48/49).

### Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `File encoding keyvalues2_noids is undefined` | Wrong studiomdl or wrong DMX encoding | Make sure you're using **SFM's** studiomdl, not SDK 2013 |
| `could not load file 'anims/hl2_female_reference.dmx'` | QC references `.dmx` but proportion files are `.smd` | Change the file extension to `.smd` in the QC |
| `too many bones` / `ERROR: too many deform bones` | Using GMod's studiomdl with >128 bone model | Switch to SFM's studiomdl |
| `$model "body" "mesh.dmx" { }` empty braces warning | Leftover from removed `flexfile` block | Remove the `{ }` — DMX doesn't need them |
| Model compiles but looks wrong in GMod | Proportion trick not applied or wrong bone names | Verify `$definebone` names match ValveBiped convention |

## Requirements

- Python 3.10+ (uses `match` statement syntax from `dataclass` union types)
- tkinter (included with standard Python on Windows)
- No external dependencies

## Building a Standalone .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "GMod PM Proportion Tool" app.py
```

The `.exe` will be in the `dist/` folder.

## How It Works

The **CaptainBigButt Method** ([Steam Guide](https://steamcommunity.com/sharedfiles/filedetails/?id=2308084980)):

GMod uses HL2 female animations for all playermodels. Custom models have different bone lengths (proportions), causing stretching/squishing. The fix:

1. Create a reference SMD with HL2 female bone positions but the model's rotations
2. Create a proportions SMD with the model's actual bone positions and rotations  
3. Use `subtract` to get a delta — since rotations are identical, only positions differ
4. Apply as an `autoplay` sequence so every animation gets the correction

This tool does all the math from the QC's `$definebone` data — no Blender, no intermediate files, instant generation.

## Credits

- **CaptainBigButt** — Original Proportion Trick method & [Steam guide](https://steamcommunity.com/sharedfiles/filedetails/?id=2308084980)
- **Bob** — [Ultimate Porting Guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3394845385) documenting DMX workflow & bone limits
- **Link2738** — Tool development

## License

This project is released into the public domain under [The Unlicense](LICENSE).
