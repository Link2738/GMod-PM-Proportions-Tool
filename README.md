# GMod PM Proportion Tool

A standalone tool that generates **CaptainBigButt's Proportion Trick** files for Garry's Mod playermodels — no Blender required.

The proportion trick fixes the stretched/squished look custom playermodels get in GMod by applying a position-only delta that adjusts bone lengths to match the HL2 female skeleton (what GMod animations expect).

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: Unlicense](https://img.shields.io/badge/license-Unlicense-green)

## What It Does

1. Reads `$definebone` entries from your decompiled QC file
2. Generates two skeleton-only SMDs:
   - `proportions.smd` — your model's bone positions & rotations
   - `hl2_female_reference.smd` — HL2 female bone positions with your model's rotations
3. Outputs a ready-to-paste QC snippet that wires everything up

Because both SMDs share identical rotations, studiomdl's `subtract` produces a **pure position delta** with zero rotation artifacts — no gimbal lock, no deformation issues.

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
- **Link2738** — Tool development

## License

This project is released into the public domain under [The Unlicense](LICENSE).
