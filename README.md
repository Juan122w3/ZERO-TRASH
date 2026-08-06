# ZERO-TRASH
# Dimensional Fidelity Testing for Zoo's Agent API

**What happens when you give a text-to-CAD agent hard numeric constraints?**
I generated PCB geometry through Zoo's Agent API with explicit dimensions and
measured the output against the spec. The models look right. The numbers don't.

## The problem I set out to explore

Text-to-CAD is judged visually — a model that *looks* like a PCB reads as success.
But engineering geometry is only useful if it holds its dimensions. I wanted to
know whether prompt-specified constraints survive generation.

## Method

I wrote prompts containing explicit, checkable constraints and compared the
generated geometry against them.

Prompt specified:
- Board: 100 mm x 80 mm (1.25:1 aspect ratio)
- 8 parallel traces, 1 mm wide, 1.5 mm pitch
- 4 circular pads, 3 mm diameter
- 2 mounting holes, 2.5 mm diameter
- Board thickness 1.6 mm

## Results

| Constraint | Specified | Generated |
|---|---|---|
| Aspect ratio | 1.25:1 | ~3:1 |
| Parallel traces | 8 | 1 serpentine polyline |
| Circular pads | 4 | none |
| Mounting holes | 2 | none |

See `outputs/` and `docs/render.png`.

**Finding: the output is visually plausible and dimensionally unfaithful.**
Every numeric constraint in the prompt was dropped. Components sit on the surface
with no pads beneath them; the trace is a decorative polyline connecting nothing.

## Notes for the Zoo team

1. **Numeric constraints in prompts are not enforced.** A round-trip validator —
   generate, measure, report deviation — would make text-to-CAD usable for
   engineering rather than visualization.
2. **No constraint-echo in the response.** The API returns geometry but no
   statement of what dimensions it believes it produced, so there's nothing to
   diff against without external measurement.
3. **Docs gap:** the Agent API docs show prompt-to-model flow but no guidance on
   constraint reliability or when to fall back to KCL for dimensioned parts.

## Honest scope

This is a two-week exploration, not a finished tool. The measurement was done by
inspection, not automated. The obvious next step is an automated harness that
parses constraints out of the prompt, measures the returned B-rep via the Engine
API, and emits a fidelity score per constraint. That's what I'd build next.

## Why PCBs

I work on conductive materials and wanted to see whether AI-native CAD could take
material-driven design constraints as input. It can take the description. It does
not yet take the numbers.

## Setup

\`\`\`bash
git clone <this-repo>
cd <this-repo>
npm install
cp .env.example .env   # add ZOO_API_KEY
npm start
\`\`\`

## Demo

[video]

## License
MIT
