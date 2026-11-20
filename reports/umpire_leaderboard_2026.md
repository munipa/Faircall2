# Umpire consistency audit, 2026

371,385 taken pitches in 2,429 games. Blocked balls included.
90 of 91 umpires have at least 1,000 calls and are rated. 0 pitches had no umpire listed.
Umpires' original calls restored on 5,686 overturned ABS challenges.

## League

- Accuracy against the measured zone: 93.5% (9.9 missed calls per game)
- Accuracy on close pitches (within 2 inches of the edge): 72.9%
- Extra strikes per 100 pitches: +0.00. This should be close to zero; it checks that the model's expectations are unbiased.
- With two strikes: -0.03; with three balls: +0.09

## Most accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 1 | Jansen Visconti | 28 | 95.0% (94.3%–95.7%) | 7.4 | 78.4% |
| 2 | Dillon Wilson | 11 | 95.0% (93.9%–96.0%) | 7.5 | 76.5% |
| 3 | Mark Ripperger | 31 | 94.9% (94.2%–95.5%) | 7.9 | 77.8% |
| 4 | Louie Krupa | 17 | 94.5% (93.6%–95.3%) | 8.5 | 76.9% |
| 5 | Edwin Moscoso | 30 | 94.5% (93.8%–95.2%) | 8.2 | 75.7% |
| 6 | Gabe Morales | 29 | 94.5% (93.8%–95.1%) | 8.0 | 75.6% |
| 7 | Tyler Jones | 24 | 94.5% (93.7%–95.1%) | 8.5 | 76.5% |
| 8 | Chris Conroy | 25 | 94.4% (93.7%–95.1%) | 8.9 | 76.2% |
| 9 | Junior Valentine | 26 | 94.4% (93.6%–95.1%) | 8.7 | 75.5% |
| 10 | Nestor Ceja | 32 | 94.3% (93.7%–95.0%) | 8.5 | 75.3% |

## Least accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 90 | John Bacon | 17 | 92.0% (90.9%–93.0%) | 11.9 | 70.3% |
| 89 | Bruce Dreckman | 28 | 92.2% (91.4%–93.0%) | 12.0 | 69.1% |
| 88 | Adrian Johnson | 22 | 92.2% (91.3%–93.1%) | 12.3 | 69.3% |
| 87 | Jen Pawol | 13 | 92.3% (91.0%–93.4%) | 11.9 | 70.7% |
| 86 | Ron Kulpa | 24 | 92.4% (91.4%–93.2%) | 11.7 | 69.2% |
| 85 | Sean Barber | 30 | 92.4% (91.6%–93.1%) | 11.7 | 69.1% |
| 84 | Hunter Wendelstedt | 30 | 92.5% (91.7%–93.2%) | 11.3 | 70.9% |
| 83 | Felix Neon | 8 | 92.5% (90.9%–93.9%) | 11.2 | 70.1% |
| 82 | Mike Estabrook | 29 | 92.6% (91.7%–93.3%) | 11.1 | 70.0% |
| 81 | Nick Mahrley | 28 | 92.6% (91.8%–93.3%) | 11.5 | 69.4% |

## Strike-calling tendencies

21 umpires call clearly more strikes than expected and 18 call clearly fewer (95% interval excludes zero).

Most extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Doug Eddings | +2.13 (+1.54 to +2.71) | +1.25 | +2.64 |
| Ron Kulpa | +2.06 (+1.41 to +2.72) | +2.72 | +2.61 |
| Rob Drake | +1.98 (+1.40 to +2.55) | +1.18 | +1.47 |
| John Bacon | +1.24 (+0.44 to +2.05) | +1.47 | +4.29 |
| Dexter Kelley | +1.16 (+0.46 to +1.87) | +0.83 | +2.25 |

Fewest extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Willie Traynor | -1.65 (-2.21 to -1.10) | -0.10 | -1.77 |
| Charlie Ramos | -1.46 (-2.12 to -0.80) | -2.42 | -2.06 |
| Nic Lentz | -1.30 (-1.85 to -0.75) | -1.07 | +1.80 |
| Derek Thomas | -1.23 (-1.91 to -0.54) | -0.51 | -1.71 |
| Tyler Jones | -1.18 (-1.83 to -0.52) | +0.01 | -1.92 |

## How to read this

- Accuracy compares each call with the measured zone; a pitch is in if any part of the ball touches it.
- Extra strikes compare each call with what the model expects umpires in general to call for the same pitch, count and batter. Positive means more strikes than the league.
- Ranks near each other are usually not meaningfully different; check whether the intervals overlap.
- This is a consistency audit, not a verdict on any umpire.
