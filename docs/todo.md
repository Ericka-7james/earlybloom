TODO: Investigate layout inconsistencies at browser zoom levels (e.g. 110%–125%)

Context:
- Layout appears correct in DevTools responsive mode
- At increased browser zoom (125%), spacing and scaling feel off on large screens

Potential causes:
- Use of fixed spacing values instead of responsive clamps
- Container max-width interaction with zoom scaling
- Font-size and rem scaling differences under zoom
- Hero / section spacing not clamped properly

Next steps:
- Audit spacing using clamp() for padding, margins, and gaps
- Test layout across zoom levels (100%, 110%, 125%, 150%)
- Verify typography scaling (rem vs px usage)
- Consider tightening max-width and spacing rhythm for large screens