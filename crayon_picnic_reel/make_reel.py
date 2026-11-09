"""Assemble the stroke frames from render_strokes.py into a 6 s, 1080x1350 (4:5) Instagram Reels mp4.

Layout: the 16:9 drawing lies as a sheet (soft drop shadow) on a crayon-paper background of the same skill.
Timeline @30 fps: 0.3 s blank paper -> 4.6 s draw-on (all strokes, evenly sampled) -> 1.1 s hold on the finished picture.

usage: python3 make_reel.py SKILL_DIR RENDER_DIR OUT.mp4
"""
import glob, os, subprocess, sys
import numpy as np
from PIL import Image, ImageFilter

skill, render, out_mp4 = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(skill, 'lib'))
from crayon import Crayon  # noqa: E402

W, H, FPS = 1080, 1350, 30
T_BLANK, T_DRAW, T_HOLD = 0.3, 4.6, 1.1
SHEET_W = 1020
SHEET_H = round(SHEET_W * 1080 / 1920)
X0, Y0 = (W - SHEET_W) // 2, (H - SHEET_H) // 2

stages = os.path.join(render, 'stages')
strokes = sorted(p for p in glob.glob(os.path.join(stages, '[0-9][0-9][0-9]_*.png')))
seq = [os.path.join(stages, '00_paper.png')] + strokes
print('frames available:', len(seq))

# background: a darker, rougher sheet of the same crayon paper
bg = Crayon(W, H, seed=3)
bg.paper(tone=(0.86, 0.82, 0.74))
bg = bg.composite().convert('RGB')
shadow = Image.new('L', (W, H), 0)
shadow.paste(90, (X0 + 6, Y0 + 12, X0 + SHEET_W + 6, Y0 + SHEET_H + 12))
shadow = shadow.filter(ImageFilter.GaussianBlur(14))
base = Image.composite(Image.new('RGB', (W, H), (60, 45, 30)), bg, shadow)


def frame(path):
    im = base.copy()
    im.paste(Image.open(path).convert('RGB').resize((SHEET_W, SHEET_H), Image.LANCZOS), (X0, Y0))
    return im


n_blank, n_draw, n_hold = round(T_BLANK * FPS), round(T_DRAW * FPS), round(T_HOLD * FPS)
order = [0] * n_blank
order += [1 + round(k * (len(seq) - 2) / (n_draw - 1)) for k in range(n_draw)]   # stroke 1 .. last stroke
order += [len(seq) - 1] * n_hold
assert len(order) == 6 * FPS, len(order)

fdir = os.path.join(render, 'reel_frames')
os.makedirs(fdir, exist_ok=True)
cache = {}
for j, i in enumerate(order):
    if i not in cache:
        cache.clear()
        cache[i] = frame(seq[i])
    cache[i].save(os.path.join(fdir, f'{j:04d}.png'), compress_level=1)

subprocess.run([
    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
    '-framerate', str(FPS), '-i', os.path.join(fdir, '%04d.png'),
    '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000',
    '-map', '0:v', '-map', '1:a', '-shortest',
    '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.1', '-preset', 'slow', '-crf', '17',
    '-pix_fmt', 'yuv420p', '-r', str(FPS), '-g', str(FPS),
    '-c:a', 'aac', '-b:a', '128k',
    '-movflags', '+faststart', out_mp4], check=True)
print('wrote', out_mp4)
