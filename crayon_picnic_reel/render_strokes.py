"""Render crayon_picnic with a snapshot after every top-level drawing call (stroke-level draw-on frames).

Runs the skill's own examples/crayon_picnic.py with --stages, but first wraps the Crayon drawing
methods so each top-level call (a line, a scribble fill, a dab, a word...) also records a stage.
Nested calls (e.g. write() calling line()) only count once.

usage: python3 render_strokes.py SKILL_DIR OUT_DIR
"""
import os, runpy, sys

skill, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
sys.path.insert(0, os.path.join(skill, 'lib'))
import crayon  # noqa: E402

DRAW = ['line', 'lines', 'scribble', 'loops', 'follow', 'dab', 'write', 'stick', 'deposit', 'burnish', 'crumbs']
depth = [0]
count = [0]


def wrap(name, fn):
    def inner(self, *a, **k):
        depth[0] += 1
        try:
            return fn(self, *a, **k)
        finally:
            depth[0] -= 1
            if depth[0] == 0:
                count[0] += 1
                self.composite().save(os.path.join(out, 'stages', f'{count[0]:03d}_{name}.png'), compress_level=1)
    return inner


for n in DRAW:
    setattr(crayon.Crayon, n, wrap(n, getattr(crayon.Crayon, n)))

# frames go straight to disk (keeps memory flat); the example's named stages would duplicate stroke frames,
# so only the first one (blank paper) is kept and saved by the example as 00_paper.png
crayon.Crayon.stage = lambda self, name: None if self.stages else self.stages.append((name, self.composite()))
os.makedirs(os.path.join(out, 'stages'), exist_ok=True)

ex = os.path.join(skill, 'examples', 'crayon_picnic.py')
sys.argv = [ex, os.path.join(out, 'final.jpg'), '--stages', os.path.join(out, 'stages')]
runpy.run_path(ex, run_name='__main__')
print('strokes:', count[0])
