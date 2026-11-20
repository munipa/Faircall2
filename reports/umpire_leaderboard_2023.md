# Umpire consistency audit, 2023

374,385 taken pitches in 2,430 games. Blocked balls included.
90 of 94 umpires have at least 1,000 calls and are rated. 0 pitches had no umpire listed.

## League

- Accuracy against the measured zone: 92.8% (11.0 missed calls per game)
- Accuracy on close pitches (within 2 inches of the edge): 73.1%
- Extra strikes per 100 pitches: +0.00. This should be close to zero; it checks that the model's expectations are unbiased.
- With two strikes: -0.05; with three balls: +0.10

## Most accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 1 | Quinn Wolcott | 29 | 94.8% (94.1%–95.4%) | 7.8 | 79.1% |
| 2 | Pat Hoberg | 29 | 94.5% (93.9%–95.2%) | 8.9 | 78.7% |
| 3 | Alex Tosi | 32 | 94.1% (93.4%–94.7%) | 9.3 | 76.4% |
| 4 | Ryan Wills | 33 | 94.0% (93.3%–94.6%) | 9.3 | 76.1% |
| 5 | Jansen Visconti | 28 | 94.0% (93.2%–94.6%) | 9.5 | 77.0% |
| 6 | Derek Thomas | 19 | 93.9% (93.0%–94.7%) | 9.3 | 74.5% |
| 7 | Tripp Gibson | 29 | 93.9% (93.2%–94.6%) | 9.4 | 75.0% |
| 8 | Alan Porter | 31 | 93.9% (93.1%–94.5%) | 9.2 | 75.8% |
| 9 | Jeremy Riggs | 24 | 93.8% (93.0%–94.6%) | 9.6 | 73.9% |
| 10 | Mike Estabrook | 29 | 93.7% (93.0%–94.4%) | 10.2 | 75.9% |

## Least accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 90 | Scott Barry | 11 | 90.1% (88.5%–91.5%) | 14.5 | 65.0% |
| 89 | Angel Hernandez | 11 | 90.7% (89.3%–92.0%) | 14.8 | 68.7% |
| 88 | Hunter Wendelstedt | 28 | 91.1% (90.2%–91.9%) | 13.9 | 69.1% |
| 87 | Larry Vanover | 11 | 91.2% (89.8%–92.4%) | 14.9 | 66.6% |
| 86 | CB Bucknor | 26 | 91.3% (90.4%–92.1%) | 13.8 | 70.5% |
| 85 | Ron Kulpa | 25 | 91.6% (90.6%–92.4%) | 13.0 | 69.7% |
| 84 | Doug Eddings | 31 | 91.6% (90.8%–92.4%) | 12.5 | 69.9% |
| 83 | Brian Walsh | 14 | 91.7% (90.5%–92.8%) | 12.9 | 71.6% |
| 82 | Brian O'Nora | 32 | 91.8% (91.0%–92.5%) | 12.3 | 68.9% |
| 81 | Paul Emmel | 10 | 91.8% (90.4%–93.0%) | 13.6 | 71.6% |

## Strike-calling tendencies

24 umpires call clearly more strikes than expected and 25 call clearly fewer (95% interval excludes zero).

Most extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Doug Eddings | +3.98 (+3.38 to +4.57) | +1.69 | +3.40 |
| Bill Miller | +2.76 (+2.17 to +3.36) | +2.40 | +1.56 |
| Lance Barrett | +2.18 (+1.60 to +2.76) | +1.47 | +2.48 |
| Gabe Morales | +1.79 (+1.17 to +2.41) | +0.16 | +2.61 |
| Jeff Nelson | +1.48 (+0.89 to +2.07) | +1.65 | +1.51 |

Fewest extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Adrian Johnson | -3.10 (-3.69 to -2.51) | -2.02 | -4.49 |
| Mark Wegner | -2.54 (-3.19 to -1.89) | -1.67 | -2.76 |
| Derek Thomas | -2.17 (-2.91 to -1.43) | -0.98 | -2.73 |
| Pat Hoberg | -2.15 (-2.73 to -1.56) | -1.49 | -2.62 |
| Edwin Moscoso | -1.81 (-2.39 to -1.24) | -1.31 | -0.01 |

## How to read this

- Accuracy compares each call with the measured zone; a pitch is in if any part of the ball touches it.
- Extra strikes compare each call with what the model expects umpires in general to call for the same pitch, count and batter. Positive means more strikes than the league.
- Ranks near each other are usually not meaningfully different; check whether the intervals overlap.
- This is a consistency audit, not a verdict on any umpire.
