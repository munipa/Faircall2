# Umpire consistency audit, 2024

366,873 taken pitches in 2,429 games. Blocked balls included.
89 of 90 umpires have at least 1,000 calls and are rated. 0 pitches had no umpire listed.

## League

- Accuracy against the measured zone: 92.6% (11.2 missed calls per game)
- Accuracy on close pitches (within 2 inches of the edge): 72.3%
- Extra strikes per 100 pitches: +0.00. This should be close to zero; it checks that the model's expectations are unbiased.
- With two strikes: -0.04; with three balls: +0.09

## Most accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 1 | Derek Thomas | 28 | 94.4% (93.6%–95.0%) | 8.9 | 76.6% |
| 2 | Alan Porter | 29 | 94.2% (93.5%–94.9%) | 8.7 | 76.8% |
| 3 | John Libka | 30 | 94.0% (93.3%–94.7%) | 9.1 | 76.4% |
| 4 | Will Little | 18 | 94.0% (93.0%–94.8%) | 8.9 | 74.9% |
| 5 | Alex Tosi | 30 | 93.9% (93.2%–94.6%) | 9.2 | 75.4% |
| 6 | Nestor Ceja | 28 | 93.9% (93.1%–94.6%) | 9.0 | 75.5% |
| 7 | Adam Hamari | 32 | 93.8% (93.1%–94.5%) | 9.3 | 75.3% |
| 8 | Jeremy Riggs | 17 | 93.8% (92.9%–94.7%) | 9.6 | 75.0% |
| 9 | Ben May | 28 | 93.8% (93.0%–94.5%) | 9.3 | 75.0% |
| 10 | Jeremie Rehak | 29 | 93.8% (93.0%–94.4%) | 9.6 | 75.2% |

## Least accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 89 | CB Bucknor | 29 | 90.9% (90.0%–91.7%) | 13.9 | 68.2% |
| 88 | Brian O'Nora | 26 | 90.9% (90.0%–91.8%) | 13.3 | 68.5% |
| 87 | Larry Vanover | 28 | 91.2% (90.3%–92.0%) | 13.4 | 68.0% |
| 86 | Roberto Ortiz | 29 | 91.2% (90.3%–92.1%) | 12.3 | 69.2% |
| 85 | Manny Gonzalez | 29 | 91.3% (90.4%–92.1%) | 13.0 | 69.9% |
| 84 | Rob Drake | 29 | 91.3% (90.4%–92.1%) | 13.1 | 68.8% |
| 83 | Laz Diaz | 30 | 91.3% (90.5%–92.1%) | 13.6 | 70.5% |
| 82 | Hunter Wendelstedt | 31 | 91.3% (90.5%–92.1%) | 13.5 | 68.7% |
| 81 | Alfonso Márquez | 31 | 91.5% (90.7%–92.3%) | 12.5 | 71.9% |
| 80 | Cory Blaser | 28 | 91.6% (90.8%–92.5%) | 12.1 | 70.6% |

## Strike-calling tendencies

22 umpires call clearly more strikes than expected and 26 call clearly fewer (95% interval excludes zero).

Most extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Doug Eddings | +2.86 (+2.26 to +3.45) | +1.40 | +2.24 |
| Mike Estabrook | +2.80 (+2.20 to +3.41) | +3.27 | +4.92 |
| Brian Walsh | +2.34 (+1.78 to +2.90) | +0.64 | +1.48 |
| Jacob Metz | +2.18 (+1.18 to +3.17) | +2.76 | +3.31 |
| Rob Drake | +2.00 (+1.39 to +2.62) | +0.58 | +0.59 |

Fewest extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Adrian Johnson | -2.12 (-2.74 to -1.51) | -1.40 | -3.68 |
| Lance Barksdale | -1.88 (-2.44 to -1.31) | -1.56 | -2.75 |
| Jonathan Parra | -1.86 (-2.61 to -1.12) | -1.36 | -2.06 |
| Alfonso Márquez | -1.67 (-2.28 to -1.07) | -2.19 | -4.04 |
| Nic Lentz | -1.63 (-2.27 to -0.99) | -0.69 | -0.91 |

## How to read this

- Accuracy compares each call with the measured zone; a pitch is in if any part of the ball touches it.
- Extra strikes compare each call with what the model expects umpires in general to call for the same pitch, count and batter. Positive means more strikes than the league.
- Ranks near each other are usually not meaningfully different; check whether the intervals overlap.
- This is a consistency audit, not a verdict on any umpire.
