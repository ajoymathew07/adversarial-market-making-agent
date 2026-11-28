# Calibration of `[agent.kalman]` on training seeds

`make calibrate`: the calibration agent on base, dev seeds 0–29, 2000 steps, 22,119 fills. It
uses only its own fills, posted quotes, centres and last trade prices. The "true" column reads
`[market]` and is a simulation-only check. The no_informed column is a diagnostic run of the same
procedure; it is not used for the config.

| Parameter | Estimated (base, committed) | True | Diagnostic: no_informed |
|---|---|---|---|
| σ (ticks/step) | 1.04 | 1.00 | 1.07 |
| λ (takers/step) | 1.01 | 1.00 noise (+0.18 informed in base) | 0.86 |
| k (1/tick) | 0.38 | 0.60 | 0.36 |
| s̄ (lots) | 3.50 | 3.00 | 2.99 |
| E[s²] (lots²) | 16.44 | 11.00 | 10.97 |

Fill-rate curve (base, both sides pooled): mean fills per resting quote at d = 1..5 ticks from the
centre are 0.327, 0.242, 0.171, 0.113, 0.071 (about 24,000 quotes at each distance).

- **k** is too low by a third in both scenarios. The agent measures distance from its own centre
  (last trade price minus its skew), not from V, and that centre is off by a few ticks. Averaging
  over that error flattens the curve. Informed flow is not the cause: no_informed gives 0.36.
- **λ** looks right in base only because two errors cancel. The same flattening lowers the
  intercept (no_informed: 0.86 against a true 1.00), and in base the informed takers' fills are
  counted as well.
- **Sizes** are too high in base because informed fills (5–10 lots) are mixed in. In no_informed
  they match the uniform 1–5 values, so censoring at our 10-lot quote size has no visible effect.
- **σ** is 4–7% high. Trade prices are our own bid or ask, and that bounce adds a fixed amount to
  each squared change; the 50-step lag dilutes it but does not remove it.
- The fit still assumes the exponential fill shape. The model-shape stress scenarios test that
  separately.
