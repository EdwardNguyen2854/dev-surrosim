# Beam validation (unperforated cantilever)

Euler-Bernoulli nominal tip displacement: 1.9048 mm; nominal root bending stress: 250.00 MPa.

Tip displacement is compared against Euler-Bernoulli theory for the same
cantilever. The fully clamped 3-D face and the distributed end traction
are known to stiffen the model slightly, so a small negative displacement
error is expected and should shrink with slenderness.

| order | mesh (mm) | status | nodes | max disp (mm) | disp error (%) | midspan |SXX| (MPa) | stress error (%) | solve (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 | SUCCESS | 888 | 0.5550 | -70.86 | 45.69 | -64.71 | 0.15 |
| 1 | 3 | SUCCESS | 1870 | 1.0708 | -43.78 | 75.09 | -42.49 | 0.33 |
| 1 | 2 | SUCCESS | 4946 | 1.3715 | -28.00 | 95.52 | -26.05 | 1.05 |
| 1 | 1.5 | SUCCESS | 9761 | 1.5367 | -19.32 | 109.48 | -11.12 | 2.34 |
| 2 | 4 | SUCCESS | 5101 | 1.8559 | -2.57 | 133.69 | +0.29 | 0.84 |
| 2 | 3 | SUCCESS | 11647 | 1.8583 | -2.44 | 131.91 | +0.52 | 2.32 |
| 2 | 2 | SUCCESS | 32710 | 1.8593 | -2.39 | 129.48 | +0.24 | 8.20 |
| 2 | 1.5 | SUCCESS | 66191 | 1.8599 | -2.35 | 128.84 | +0.64 | 20.52 |

## Slenderness sweep (quadratic, mesh = T/4)

| length (mm) | L/T | status | max disp (mm) | disp error (%) | midspan |SXX| error (%) |
| --- | --- | --- | --- | --- | --- |
| 240 | 40 | SUCCESS | 15.0292 | -1.37 | +0.08 |

## Conclusion

Quadratic mesh convergence: tip displacement changes 0.033% between 2 mm and 1.5 mm. Finest quadratic tip displacement differs from Euler-Bernoulli by -2.35% (expected: fully clamped 3-D face is stiffer than the ideal beam clamp). Mid-span outer-fiber |SXX| agrees with beam theory within +0.64%. At L/T=40 the tip displacement gap is -1.37%, shrinking with slenderness.

