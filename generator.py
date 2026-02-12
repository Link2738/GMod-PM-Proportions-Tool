"""GMod PM Proportion Tool — Backend Engine

Implements the CaptainBigButt Proportion Trick method:
https://steamcommunity.com/sharedfiles/filedetails/?id=2308084980

Generates two skeleton-only SMD animation files directly from
$definebone data (no Blender required — pure math from QC bone
definitions):

  proportions.smd          = model positions + model rotations
  hl2_female_reference.smd = HL2 positions   + model rotations

Because both files share identical rotations, studiomdl's
"subtract" produces a pure position delta (zero rotation).

SMD is used because the proportion trick only contains the ~53
matched ValveBiped bones — well under the 128-bone compile limit.
Works with any studiomdl compiler (GMod SDK, SFM, etc.).
"""

__version__ = '1.2.0'

import math
import os
import re
from dataclasses import dataclass, field
from typing import Optional, Callable, List



# ------------------------------------------------------------------
# $definebone QC parser
# ------------------------------------------------------------------

_DEFINEBONE_RE = re.compile(
    r'\$definebone\s+'
    r'"([^"]+)"\s+'            # bone name
    r'"([^"]*)"\s+'            # parent name (empty = root)
    r'([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+'   # pos x y z
    r'([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)',      # rot x y z (degrees)
    re.IGNORECASE,
)


def parse_definebones(qc_path_or_text, *, is_text=False):
    """Parse $definebone lines from a QC file or raw text.

    Returns dict keyed by bone name (insertion-ordered):
        {name: {parent, position[3], rotation_deg[3], rotation_rad[3]}}
    """
    if is_text:
        text = qc_path_or_text
    else:
        with open(qc_path_or_text, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()

    bones = {}
    for m in _DEFINEBONE_RE.finditer(text):
        name = m.group(1)
        parent = m.group(2) or None
        pos = [float(m.group(3)), float(m.group(4)), float(m.group(5))]
        rot_deg = [float(m.group(6)), float(m.group(7)), float(m.group(8))]
        rot_rad = [math.radians(d) for d in rot_deg]
        bones[name] = {
            'parent': parent,
            'position': pos,
            'rotation_deg': rot_deg,
            'rotation_rad': rot_rad,
        }
    return bones


# ------------------------------------------------------------------
# Core ValveBiped bones used by the proportion trick
# ------------------------------------------------------------------

_VALVEBIPEDS = [
    'ValveBiped.Bip01_Pelvis',
    'ValveBiped.Bip01_Spine',
    'ValveBiped.Bip01_Spine1',
    'ValveBiped.Bip01_Spine2',
    'ValveBiped.Bip01_Spine4',
    'ValveBiped.Bip01_Neck1',
    'ValveBiped.Bip01_Head1',
    'ValveBiped.Bip01_R_Clavicle',
    'ValveBiped.Bip01_R_UpperArm',
    'ValveBiped.Bip01_R_Forearm',
    'ValveBiped.Bip01_R_Hand',
    'ValveBiped.Bip01_R_Finger0',
    'ValveBiped.Bip01_R_Finger01',
    'ValveBiped.Bip01_R_Finger02',
    'ValveBiped.Bip01_R_Finger1',
    'ValveBiped.Bip01_R_Finger11',
    'ValveBiped.Bip01_R_Finger12',
    'ValveBiped.Bip01_R_Finger2',
    'ValveBiped.Bip01_R_Finger21',
    'ValveBiped.Bip01_R_Finger22',
    'ValveBiped.Bip01_R_Finger3',
    'ValveBiped.Bip01_R_Finger31',
    'ValveBiped.Bip01_R_Finger32',
    'ValveBiped.Bip01_R_Finger4',
    'ValveBiped.Bip01_R_Finger41',
    'ValveBiped.Bip01_R_Finger42',
    'ValveBiped.Bip01_L_Clavicle',
    'ValveBiped.Bip01_L_UpperArm',
    'ValveBiped.Bip01_L_Forearm',
    'ValveBiped.Bip01_L_Hand',
    'ValveBiped.Bip01_L_Finger0',
    'ValveBiped.Bip01_L_Finger01',
    'ValveBiped.Bip01_L_Finger02',
    'ValveBiped.Bip01_L_Finger1',
    'ValveBiped.Bip01_L_Finger11',
    'ValveBiped.Bip01_L_Finger12',
    'ValveBiped.Bip01_L_Finger2',
    'ValveBiped.Bip01_L_Finger21',
    'ValveBiped.Bip01_L_Finger22',
    'ValveBiped.Bip01_L_Finger3',
    'ValveBiped.Bip01_L_Finger31',
    'ValveBiped.Bip01_L_Finger32',
    'ValveBiped.Bip01_L_Finger4',
    'ValveBiped.Bip01_L_Finger41',
    'ValveBiped.Bip01_L_Finger42',
    'ValveBiped.Bip01_R_Thigh',
    'ValveBiped.Bip01_R_Calf',
    'ValveBiped.Bip01_R_Foot',
    'ValveBiped.Bip01_R_Toe0',
    'ValveBiped.Bip01_L_Thigh',
    'ValveBiped.Bip01_L_Calf',
    'ValveBiped.Bip01_L_Foot',
    'ValveBiped.Bip01_L_Toe0',
]

_VALVEBIPEDS_SET = set(_VALVEBIPEDS)


# ------------------------------------------------------------------
# Built-in HL2 female reference skeleton
# ------------------------------------------------------------------

_HL2_FEMALE_QC = """\
$definebone "ValveBiped.Bip01_Pelvis" "" -0.000005 -0.78846 37.913784 0 0 89.999982
$definebone "ValveBiped.Bip01_Spine" "ValveBiped.Bip01_Pelvis" 0.000005 4.212788 -1.689857 -1.602964 89.999982 89.999982
$definebone "ValveBiped.Bip01_Spine1" "ValveBiped.Bip01_Spine" 3.837406 0 0 0 -6.452307 0
$definebone "ValveBiped.Bip01_Spine2" "ValveBiped.Bip01_Spine1" 3.617855 0 0 0 -0.723932 0
$definebone "ValveBiped.Bip01_Spine4" "ValveBiped.Bip01_Spine2" 7.539783 0 0 0 8.927426 0
$definebone "ValveBiped.Bip01_Neck1" "ValveBiped.Bip01_Spine4" 3.178295 0.000001 0 0 12.841531 179.999855
$definebone "ValveBiped.Bip01_Head1" "ValveBiped.Bip01_Neck1" 2.97028 0.000002 0 0 6.295659 0
$definebone "ValveBiped.forward" "ValveBiped.Bip01_Head1" 0 0 0 0 -76 -90.000003
$definebone "ValveBiped.Bip01_L_Clavicle" "ValveBiped.Bip01_Spine4" 2.023708 0.90746 0.852579 -76.44039 166.164378 93.870917
$definebone "ValveBiped.Bip01_L_UpperArm" "ValveBiped.Bip01_L_Clavicle" 4.983671 0 0 12.460347 -43.013512 -87.036698
$definebone "ValveBiped.Bip01_L_Forearm" "ValveBiped.Bip01_L_UpperArm" 11.123055 0.000002 -0.000004 0.000024 -5.909027 0.000001
$definebone "ValveBiped.Bip01_L_Hand" "ValveBiped.Bip01_L_Forearm" 11.208265 -0.000001 -0.000038 -2.211881 2.080013 86.253992
$definebone "ValveBiped.Anim_Attachment_LH" "ValveBiped.Bip01_L_Hand" 2.67609 -1.71244 0 -0.00001 90.000043 90.00003
$definebone "ValveBiped.Bip01_R_Clavicle" "ValveBiped.Bip01_Spine4" 2.023712 0.907463 -0.852528 76.440506 166.163749 -97.982465
$definebone "ValveBiped.Bip01_R_UpperArm" "ValveBiped.Bip01_R_Clavicle" 4.983665 -0.000008 0 -9.640071 -43.598002 90.084492
$definebone "ValveBiped.Bip01_R_Forearm" "ValveBiped.Bip01_R_UpperArm" 11.123062 0 0.000008 -0.000051 -5.909033 -0.000003
$definebone "ValveBiped.Bip01_R_Hand" "ValveBiped.Bip01_R_Forearm" 11.208311 -0.000001 0.000011 2.211372 2.080004 -85.770073
$definebone "ValveBiped.Anim_Attachment_RH" "ValveBiped.Bip01_R_Hand" 2.676098 -1.712452 0 0.000012 -89.999893 -89.999982
$definebone "ValveBiped.Bip01_L_Thigh" "ValveBiped.Bip01_Pelvis" 3.984014 0 -0.000003 2.966031 -92.308197 -89.999982
$definebone "ValveBiped.Bip01_L_Calf" "ValveBiped.Bip01_L_Thigh" 15.94002 0 0 0 2.959556 0
$definebone "ValveBiped.Bip01_L_Foot" "ValveBiped.Bip01_L_Calf" 17.709562 0 0 -3.776628 -62.111978 0.551821
$definebone "ValveBiped.Bip01_L_Toe0" "ValveBiped.Bip01_L_Foot" 6.203997 0.000001 0 0.053513 -28.677396 -0.638641
$definebone "ValveBiped.Bip01_R_Thigh" "ValveBiped.Bip01_Pelvis" -3.984013 0.000008 0.000007 2.966031 -87.691938 -89.999982
$definebone "ValveBiped.Bip01_R_Calf" "ValveBiped.Bip01_R_Thigh" 15.940014 0 0 0 2.959557 0
$definebone "ValveBiped.Bip01_R_Foot" "ValveBiped.Bip01_R_Calf" 17.70956 0 0 3.77585 -62.248951 0.05128
$definebone "ValveBiped.Bip01_R_Toe0" "ValveBiped.Bip01_R_Foot" 6.203997 0 0 -0.354375 -28.587325 -4.50633
$definebone "ValveBiped.Bip01_L_Finger4" "ValveBiped.Bip01_L_Hand" 3.549248 0.198826 -1.489471 21.265186 0.597179 -12.141559
$definebone "ValveBiped.Bip01_L_Finger41" "ValveBiped.Bip01_L_Finger4" 1.219001 0.000004 0 5.585326 -21.005716 -0.264289
$definebone "ValveBiped.Bip01_L_Finger42" "ValveBiped.Bip01_L_Finger41" 0.680004 0 0 4.983486 -9.905281 0.651067
$definebone "ValveBiped.Bip01_L_Finger3" "ValveBiped.Bip01_L_Hand" 3.698013 0.267559 -0.72898 14.909644 -7.176078 -4.669961
$definebone "ValveBiped.Bip01_L_Finger31" "ValveBiped.Bip01_L_Finger3" 1.749004 0 -0.000001 1.552391 -10.89554 0.01218
$definebone "ValveBiped.Bip01_L_Finger32" "ValveBiped.Bip01_L_Finger31" 0.959999 0 -0.000001 2.257584 -13.628772 0.133186
$definebone "ValveBiped.Bip01_L_Finger2" "ValveBiped.Bip01_L_Hand" 3.768507 0.152546 0.071384 1.624114 -0.196891 5.042308
$definebone "ValveBiped.Bip01_L_Finger21" "ValveBiped.Bip01_L_Finger2" 2.038003 -0.000004 0 -0.250149 -32.972588 0.086745
$definebone "ValveBiped.Bip01_L_Finger22" "ValveBiped.Bip01_L_Finger21" 1.067005 -0.000002 0 -0.324978 -5.671931 -0.071332
$definebone "ValveBiped.Bip01_L_Finger1" "ValveBiped.Bip01_L_Hand" 3.783928 -0.017258 0.794555 -12.383867 3.590763 16.23641
$definebone "ValveBiped.Bip01_L_Finger11" "ValveBiped.Bip01_L_Finger1" 1.629002 -0.000004 0.000001 -3.819812 -26.858746 1.078974
$definebone "ValveBiped.Bip01_L_Finger12" "ValveBiped.Bip01_L_Finger11" 0.955999 0 0.000001 -3.99468 -9.74192 0.00005
$definebone "ValveBiped.Bip01_L_Finger0" "ValveBiped.Bip01_L_Hand" 1.258966 -0.297985 1.252593 -30.375159 -37.494593 -73.854726
$definebone "ValveBiped.Bip01_L_Finger01" "ValveBiped.Bip01_L_Finger0" 1.393003 0 0 0.115968 -2.497489 -0.000028
$definebone "ValveBiped.Bip01_L_Finger02" "ValveBiped.Bip01_L_Finger01" 1.100006 0 -0.000002 0.752234 -16.433293 -0.000039
$definebone "ValveBiped.Bip01_R_Finger4" "ValveBiped.Bip01_R_Hand" 3.549276 0.211403 1.487672 -21.265152 0.597118 12.141559
$definebone "ValveBiped.Bip01_R_Finger41" "ValveBiped.Bip01_R_Finger4" 1.219007 -0.000004 0 -5.58529 -21.005748 0.264301
$definebone "ValveBiped.Bip01_R_Finger42" "ValveBiped.Bip01_R_Finger41" 0.680002 0.000002 0 -4.983441 -9.905291 -0.651057
$definebone "ValveBiped.Bip01_R_Finger3" "ValveBiped.Bip01_R_Hand" 3.698029 0.273712 0.726624 -14.90961 -7.176134 4.669963
$definebone "ValveBiped.Bip01_R_Finger31" "ValveBiped.Bip01_R_Finger3" 1.749004 -0.000004 0 -1.552356 -10.895572 -0.012171
$definebone "ValveBiped.Bip01_R_Finger32" "ValveBiped.Bip01_R_Finger31" 0.959999 0.000002 0 -2.257543 -13.628769 -0.133181
$definebone "ValveBiped.Bip01_R_Finger2" "ValveBiped.Bip01_R_Hand" 3.768513 0.151951 -0.07274 -1.624103 -0.196947 -5.042302
$definebone "ValveBiped.Bip01_R_Finger21" "ValveBiped.Bip01_R_Finger2" 2.038005 -0.000004 0 0.250168 -32.972547 -0.086747
$definebone "ValveBiped.Bip01_R_Finger22" "ValveBiped.Bip01_R_Finger21" 1.067001 0.000002 0 0.324998 -5.671872 0.071329
$definebone "ValveBiped.Bip01_R_Finger1" "ValveBiped.Bip01_R_Hand" 3.783916 -0.023956 -0.794453 12.383856 3.590692 -16.236406
$definebone "ValveBiped.Bip01_R_Finger11" "ValveBiped.Bip01_R_Finger1" 1.629004 -0.000008 0 3.819813 -26.858735 -1.078982
$definebone "ValveBiped.Bip01_R_Finger12" "ValveBiped.Bip01_R_Finger11" 0.955999 0.000002 0 3.994679 -9.741871 -0.000053
$definebone "ValveBiped.Bip01_R_Finger0" "ValveBiped.Bip01_R_Hand" 1.258947 -0.308548 -1.250056 30.375111 -37.494559 73.854726
$definebone "ValveBiped.Bip01_R_Finger01" "ValveBiped.Bip01_R_Finger0" 1.393003 0.000004 -0.000002 -0.115952 -2.497446 0.000022
$definebone "ValveBiped.Bip01_R_Finger02" "ValveBiped.Bip01_R_Finger01" 1.100004 0.000002 0.000002 -0.75221 -16.433244 0.000022
$definebone "ValveBiped.Bip01_L_Trapezius" "ValveBiped.Bip01_L_Clavicle" 4.271703 0.000004 0 0 -0.000009 0
$definebone "ValveBiped.Bip01_L_Ulna" "ValveBiped.Bip01_L_Forearm" 5.604147 0 -0.000004 0.000029 0.000002 -1.769064
$definebone "ValveBiped.Bip01_R_Ulna" "ValveBiped.Bip01_R_Forearm" 5.604155 -0.000001 0.000008 -0.000063 -0.000006 2.001338
$definebone "ValveBiped.Bip01_L_Wrist" "ValveBiped.Bip01_L_Forearm" 11.208296 0 -0.000008 0.000029 0.000002 -3.296971
$definebone "ValveBiped.Bip01_L_Bicep" "ValveBiped.Bip01_L_UpperArm" 5.560005 -0.7 -0.500004 0.000029 0.000006 0.000003
$definebone "ValveBiped.Bip01_L_Latt" "ValveBiped.Bip01_Spine2" 2.132019 1.532022 5 0 0 0
$definebone "ValveBiped.Bip01_R_Elbow" "ValveBiped.Bip01_R_UpperArm" 11.12307 0 0.000008 -0.000043 -5.733191 -0.000003
$definebone "ValveBiped.Bip01_R_Latt" "ValveBiped.Bip01_Spine2" 2.132023 1.532021 -5 0 0 0
$definebone "ValveBiped.Bip01_L_Shoulder" "ValveBiped.Bip01_L_UpperArm" 1.500004 0 0 0.000029 0.000006 0.000003
$definebone "ValveBiped.Bip01_R_Wrist" "ValveBiped.Bip01_R_Forearm" 11.208307 -0.000001 0.000011 -0.000063 -0.000006 3.73402
$definebone "ValveBiped.Bip01_L_Elbow" "ValveBiped.Bip01_L_UpperArm" 11.123062 0.000001 -0.000008 0.000027 -5.734216 0
$definebone "ValveBiped.Bip01_R_Trapezius" "ValveBiped.Bip01_R_Clavicle" 4.271699 -0.000011 0 0.000001 -0.000015 0.000001
$definebone "ValveBiped.Bip01_R_Shoulder" "ValveBiped.Bip01_R_UpperArm" 1.500004 0 0 -0.000046 -0.000003 -0.000008
$definebone "ValveBiped.Bip01_R_Bicep" "ValveBiped.Bip01_R_UpperArm" 5.560005 -0.700002 0.500004 -0.000046 -0.000003 -0.000008
"""

_HL2_FEMALE_REF = None


def _get_hl2_female_reference():
    """Return the built-in HL2 female reference skeleton (cached)."""
    global _HL2_FEMALE_REF
    if _HL2_FEMALE_REF is None:
        _HL2_FEMALE_REF = parse_definebones(_HL2_FEMALE_QC, is_text=True)
    return _HL2_FEMALE_REF


# ------------------------------------------------------------------
# SMD writer
# ------------------------------------------------------------------

def _write_smd(filepath, bone_data):
    """Write a single-frame skeleton-only SMD.

    bone_data: list of (name, parent_idx, [px,py,pz], [rx,ry,rz])
    """
    with open(filepath, 'w', newline='\n') as f:
        f.write("version 1\n")
        f.write("nodes\n")
        for i, (name, pid, _, _) in enumerate(bone_data):
            f.write(f'  {i} "{name}" {pid}\n')
        f.write("end\n")
        f.write("skeleton\n")
        f.write("time 0\n")
        for i, (_, _, pos, rot) in enumerate(bone_data):
            f.write(
                f"  {i}"
                f"  {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}"
                f"  {rot[0]:.6f} {rot[1]:.6f} {rot[2]:.6f}\n"
            )
        f.write("end\n")


# ------------------------------------------------------------------
# IK chain detection
# ------------------------------------------------------------------

def _detect_ikchains(qc_path):
    """Check if a QC file defines $ikchain entries."""
    try:
        with open(qc_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.strip().lower().startswith('$ikchain'):
                    return True
    except Exception:
        pass
    return False


# ------------------------------------------------------------------
# QC snippet writer
# ------------------------------------------------------------------

def _write_qc_snippet(filepath, anims_subfolder, has_ikchains=True):
    """Write a QC snippet for the CaptainBigButt proportion trick method."""
    hl2_ref_path = f'{anims_subfolder}/hl2_female_reference.smd'
    prop_path = f'{anims_subfolder}/proportions.smd'

    with open(filepath, 'w', newline='\n', encoding='utf-8') as f:
        f.write('// -- Corrective Proportion Trick (CaptainBigButt method) --\n')
        f.write('// Paste this AFTER your $sequence "reference" line.\n')
        f.write('//\n')
        f.write('// hl2_female_reference.smd = HL2 skeleton with model rotations\n')
        f.write('// proportions.smd         = model skeleton (core biped only)\n')
        f.write('// The delta = model positions - HL2 positions (zero rotation).\n')
        f.write('//\n')
        if has_ikchains:
            f.write('// $ikchain detected -- make sure these are defined before this block:\n')
            f.write('//   $ikchain "rhand" "ValveBiped.Bip01_R_Hand" ...\n')
            f.write('//   $ikchain "lhand" "ValveBiped.Bip01_L_Hand" ...\n')
            f.write('//   $ikchain "rfoot" "ValveBiped.Bip01_R_Foot" ...\n')
            f.write('//   $ikchain "lfoot" "ValveBiped.Bip01_L_Foot" ...\n')
            f.write('//   $ikautoplaylock "rfoot" 0.5 0.1\n')
            f.write('//   $ikautoplaylock "lfoot" 0.5 0.1\n')
            f.write('//\n')
        f.write(f'\n$sequence hl2_ref "{hl2_ref_path}" fps 1 hidden\n')
        f.write(f'\n$animation a_proportions "{prop_path}" subtract hl2_ref 0\n')
        f.write('\n$sequence proportions a_proportions delta autoplay\n')
        f.write('\n$Sequence "ragdoll" {\n')
        f.write(f'\t"{hl2_ref_path}"\n')
        f.write('\tactivity "ACT_DIERAGDOLL" 1\n')
        f.write('\tfadein 0.2\n')
        f.write('\tfadeout 0.2\n')
        f.write('\tfps 30\n')
        f.write('}\n')


# ------------------------------------------------------------------
# Core SMD generation (pure math from $definebone data)
# ------------------------------------------------------------------

def _generate_proportion_smds(model_bones, ref_bones, proportions_path, hl2_ref_path):
    """Generate both proportion trick SMDs from $definebone data.

    proportions.smd          = model positions + model rotations
    hl2_female_reference.smd = HL2 positions   + model rotations

    Only includes core ValveBiped bones present in BOTH skeletons.
    Returns the number of bones written.
    """
    model_lower = {k.lower(): k for k in model_bones}

    # Filter to bones in _VALVEBIPEDS present in both model and HL2 ref
    matched_bones = []
    for vb_name in _VALVEBIPEDS:
        if vb_name in ref_bones and vb_name.lower() in model_lower:
            matched_bones.append(vb_name)

    if not matched_bones:
        return 0

    matched_set = set(matched_bones)
    name_to_idx = {name: i for i, name in enumerate(matched_bones)}

    def find_parent_idx(bone_name):
        """Walk up HL2 hierarchy to find nearest parent in the matched set."""
        parent = ref_bones[bone_name]['parent']
        while parent:
            if parent in matched_set:
                return name_to_idx[parent]
            parent = ref_bones.get(parent, {}).get('parent')
        return -1

    proportions_data = []
    hl2_ref_data = []

    for bone_name in matched_bones:
        model_name = model_lower[bone_name.lower()]
        model_bone = model_bones[model_name]
        ref_bone = ref_bones[bone_name]
        pid = find_parent_idx(bone_name)

        # Shared rotation from model's $definebone
        # Convert: $definebone (X,Y,Z) deg -> SMD (Z,X,Y) rad
        r = model_bone['rotation_rad']
        smd_rot = [r[2], r[0], r[1]]

        proportions_data.append(
            (bone_name, pid, list(model_bone['position']), list(smd_rot))
        )
        hl2_ref_data.append(
            (bone_name, pid, list(ref_bone['position']), list(smd_rot))
        )

    os.makedirs(os.path.dirname(proportions_path) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(hl2_ref_path) or '.', exist_ok=True)
    _write_smd(proportions_path, proportions_data)
    _write_smd(hl2_ref_path, hl2_ref_data)

    return len(matched_bones)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

@dataclass
class AnalysisResult:
    """Results from analyzing a decompiled model's QC file."""
    model_name: str
    total_bones: int
    matched_bones: List[str]
    custom_bones: List[str]
    has_ikchains: bool

    @property
    def matched_count(self):
        return len(self.matched_bones)

    @property
    def custom_count(self):
        return len(self.custom_bones)


@dataclass
class GenerateResult:
    """Results from generating proportion trick files."""
    bone_count: int
    proportions_path: str
    hl2_ref_path: str
    snippet_path: str
    snippet_text: str


def analyze_qc(qc_path: str) -> AnalysisResult:
    """Analyze a decompiled model's QC for skeleton compatibility.

    Returns an AnalysisResult with matched/custom bone lists.
    Raises FileNotFoundError if QC doesn't exist.
    Raises ValueError if no $definebone lines found.
    """
    if not os.path.isfile(qc_path):
        raise FileNotFoundError(f"QC file not found: {qc_path}")

    model_bones = parse_definebones(qc_path)
    if not model_bones:
        raise ValueError(f"No $definebone lines found in {qc_path}")

    matched = []
    custom = []
    for name in model_bones:
        if name in _VALVEBIPEDS_SET:
            matched.append(name)
        else:
            custom.append(name)

    return AnalysisResult(
        model_name=os.path.splitext(os.path.basename(qc_path))[0],
        total_bones=len(model_bones),
        matched_bones=matched,
        custom_bones=custom,
        has_ikchains=_detect_ikchains(qc_path),
    )


def generate_files(qc_path: str, output_dir: str, *,
                   anims_subfolder: str = 'anims',
                   log_callback: Optional[Callable] = None) -> GenerateResult:
    """Generate all proportion trick files for a decompiled model.

    Creates:
      <output_dir>/<anims>/proportions.smd
      <output_dir>/<anims>/hl2_female_reference.smd
      <output_dir>/corrective_qc_snippet.txt

    Returns a GenerateResult with paths and bone count.
    Raises FileNotFoundError if QC doesn't exist.
    Raises ValueError if no $definebone lines or no matching bones.
    """
    log = log_callback or (lambda m: None)

    if not os.path.isfile(qc_path):
        raise FileNotFoundError(f"QC file not found: {qc_path}")

    ref_bones = _get_hl2_female_reference()
    model_bones = parse_definebones(qc_path)

    if not model_bones:
        raise ValueError(f"No $definebone lines found in {qc_path}")

    model_name = os.path.splitext(os.path.basename(qc_path))[0]
    log(f'[INFO] Model: {model_name}')
    log(f'[INFO] Target skeleton: {len(model_bones)} bones')
    log(f'[INFO] Reference skeleton: {len(ref_bones)} bones')

    # Count matches
    matched = [n for n in model_bones if n in _VALVEBIPEDS_SET]
    custom = [n for n in model_bones if n not in _VALVEBIPEDS_SET]
    log(f'[INFO] Matched ValveBiped: {len(matched)}/{len(model_bones)}')

    if not matched:
        raise ValueError("No matching ValveBiped bones found — incompatible skeleton.")

    if custom:
        preview = ', '.join(custom[:6])
        extra = f' ... +{len(custom) - 6} more' if len(custom) > 6 else ''
        log(f'[INFO] Custom bones ({len(custom)}): {preview}{extra}')

    os.makedirs(output_dir, exist_ok=True)
    anims_dir = os.path.join(output_dir, anims_subfolder)

    proportions_path = os.path.join(anims_dir, 'proportions.smd')
    hl2_ref_path = os.path.join(anims_dir, 'hl2_female_reference.smd')

    log('[INFO] Format: SMD')
    bone_count = _generate_proportion_smds(
        model_bones, ref_bones, proportions_path, hl2_ref_path
    )
    log(f'[DONE] proportions.smd ({bone_count} bones)')
    log(f'[DONE] hl2_female_reference.smd ({bone_count} bones)')

    # 2. Write QC snippet
    has_ik = _detect_ikchains(qc_path)
    snippet_path = os.path.join(output_dir, 'corrective_qc_snippet.txt')
    _write_qc_snippet(snippet_path, anims_subfolder, has_ikchains=has_ik)
    log(f'[DONE] corrective_qc_snippet.txt')

    if has_ik:
        log('[INFO] $ikchain detected — see snippet for notes.')

    # Read snippet text for clipboard support
    with open(snippet_path, 'r', encoding='utf-8') as f:
        snippet_text = f.read()

    log('')
    log('[DONE] All files generated successfully.')
    log(f'[INFO] Output: {output_dir}')
    log('[INFO] Paste corrective_qc_snippet.txt into your QC and recompile.')

    return GenerateResult(
        bone_count=bone_count,
        proportions_path=proportions_path,
        hl2_ref_path=hl2_ref_path,
        snippet_path=snippet_path,
        snippet_text=snippet_text,
    )
