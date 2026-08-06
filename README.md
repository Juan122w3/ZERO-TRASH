# Dimensional Fidelity Testing for Zoo's Text-to-CAD API

**Text-to-CAD is judged by eye. Engineering geometry is judged by calipers.**
This project measures the gap between the two.

I generated the same PCB specification twice through Zoo's Text-to-CAD API — once
phrased as design intent, once phrased as CAD operations — and measured both outputs
against the numbers in the prompt. The phrasing changed the geometry more than the
specification did.

![Prompt A vs Prompt B](docs/comparison.png)

---

## The problem

A model that *looks* like a PCB reads as success. But geometry is only useful downstream
if it holds its dimensions. Before building anything on top of a text-to-CAD pipeline,
I wanted to know a simple thing: **do the numbers in the prompt survive generation?**

This matters for my own work. I develop conductive materials, and the reason I care
about AI-native CAD is the possibility of feeding material-driven constraints straight
into geometry. That only works if constraints are constraints.

## Method

Two prompts, one target part, identical geometry requested:

| | Phrasing |
|---|---|
| **Prompt A** | Design intent — *"design a PCB for a 3D printer controller, 8 parallel traces, optimized for thermal dissipation"* |
| **Prompt B** | CAD operations — sketch/extrude/pattern with absolute coordinates and a declared origin |

Target geometry for both:

- Board 100 x 80 x 1.6 mm (aspect ratio 1.25:1)
- 8 traces, 1 mm wide, 2.5 mm pitch centre-to-centre
- 4 circular pads, 3 mm diameter, collinear at Y = 65 mm
- 2 mounting holes, 2.5 mm diameter

Both prompts verbatim in [`prompts/`](prompts/). Both raw outputs in [`outputs/`](outputs/).

## Results

### Prompt A — design intent

![Prompt A output](docs/prompt-a.png)

| Constraint | Specified | Generated | |
|---|---|---|---|
| Aspect ratio | 1.25:1 | ~3:1 | ✗ |
| Parallel traces | 8 | 1 serpentine polyline | ✗ |
| Circular pads | 4 | none | ✗ |
| Mounting holes | 2 | none | ✗ |
| Spurious components | none | ~15 chips and packages | ✗ |

Visually plausible, dimensionally unfaithful. Every numeric constraint was dropped.
Surface-mount packages sit on the board with no pads beneath them; the trace is a
decorative polyline that connects nothing. As a render it is convincing. As a board
it is meaningless.

### Prompt B — CAD operations

![Prompt B output](docs/prompt-b.png)

| Constraint | Specified | Generated | |
|---|---|---|---|
| Aspect ratio | 1.25:1 | ~1.25:1 | ✓ |
| Board thickness | 1.6 mm | held | ✓ |
| Parallel traces | 8 independent | 8 parallel, joined at ends into one serpentine path | ~ |
| Circular pads | 4 collinear at Y=65 | 4 present, distributed diagonally | ~ |
| Mounting holes | 2 | 2 | ✓ |
| Spurious components | none | none | ✓ |

Operation-level phrasing recovered most of the specification. Board dimensions, hole
count, and the no-decoration constraint all held.

**The two remaining failures are the same failure.** Counts and shapes survive.
Positions do not. Four pads were produced — correct in number and diameter — and then
placed diagonally instead of along the specified line. Eight traces were produced at the
correct pitch, and then joined end-to-end into a single conductor rather than left as
eight independent ones.

## The finding

> **Counts survive. Coordinates don't.**

Across both prompts the model reliably honours *how many* and *what shape*, and reliably
discards *where*. That is a sharper and more actionable failure mode than "constraints
are ignored" — it points at the coordinate arguments not reaching the geometry step,
rather than at general prompt non-compliance.

For an electrical part, that distinction is the difference between a render and a board.

## Notes for the Zoo team

See [`findings/api-notes.md`](findings/api-notes.md) for the full write-up. Summary:

1. **Numeric constraints are not enforced or checked.** Nothing in the pipeline compares
   generated geometry against stated dimensions.
2. **No constraint echo in the response.** The API returns geometry but never states what
   dimensions it believes it produced, so there is nothing to diff against without
   measuring externally.
3. **Phrasing appears to outweigh content.** If operation-level language reliably beats
   intent-level language, that belongs in the docs. Nothing currently signals it.
4. **The REST Text-to-CAD endpoint is marked `deprecated` and `hidden` in the API
   reference**, which recommends the `/ws/ml/copilot` websocket instead — but the official
   Python tutorial still teaches the REST/SDK flow, with no deprecation notice. A developer
   following the tutorial builds on a deprecated path without knowing it.
5. **Environment variable naming is inconsistent** across docs and examples
   (`ZOO_API_TOKEN` vs `ZOO_API_KEY`).
6. **The official Python tutorial does not run against the current SDK.** It polls with
   `get_text_to_cad_model_for_user`; `kittycad 1.4.0` exposes
   `get_text_to_cad_part_for_user`. The crash lands *after* submission succeeds, leaving
   a billed job in flight. `measure.py` resolves the method name at runtime to survive
   both.
7. **Makeathon credits expire at the submission deadline, but judging runs for another
   week.** During the judging window neither participants nor judges can execute a
   submitted repository without spending their own credits.

## Honest scope

Two prompts, one part, measured by inspection rather than by an automated harness.
This is an observation, not a benchmark — n=2 shows a direction, not an effect size.

[`measure.py`](measure.py) is the first step toward the real version: it drives both
prompts through the documented SDK and archives every response. The measurement itself
is still manual. Completing it means parsing constraints out of the prompt, measuring
the returned B-rep through the Engine API, and emitting a per-constraint fidelity score.
Run that across a prompt corpus and you have an actual reliability benchmark for
dimensioned text-to-CAD.

That is what I would build next, and it is the reason I ran this at all.

## Reproducing

```bash
pip install -r requirements.txt

export ZOO_API_TOKEN=your_token_here      # macOS / Linux
$env:ZOO_API_TOKEN = "your_token_here"    # PowerShell

python measure.py
```

**Note on credits.** The geometry documented above was generated during the makeathon
window. Running `measure.py` afterwards returns HTTP 402 — makeathon credits are removed
at the submission deadline (see API note 7). The script reproduces the *process*; it will
not reproduce the *results* without an account that has API credits available.

Outputs are written to `outputs/` along with `outputs/run_log.json`, which records the
prompt, request ID, status, timings and the SDK polling method resolved at runtime. `outputs/` is tracked in
this repository on purpose — the artifacts are the evidence.

## Demo

<!-- Drag your video file into this section using GitHub's README editor. -->
<!-- If you have no video, delete this comment and leave the images above as the demo. -->

## License

MIT — see [LICENSE](LICENSE).
