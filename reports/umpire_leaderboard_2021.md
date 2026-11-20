# Umpire consistency audit, 2021

370,554 taken pitches in 2,427 games. Blocked balls included.
94 of 99 umpires have at least 1,000 calls and are rated. 0 pitches had no umpire listed.

## League

- Accuracy against the measured zone: 92.2% (11.9 missed calls per game)
- Accuracy on close pitches (within 2 inches of the edge): 71.0%
- Extra strikes per 100 pitches: -0.00. This should be close to zero; it checks that the model's expectations are unbiased.
- With two strikes: -0.05; with three balls: +0.11

## Most accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 1 | John Libka | 32 | 94.5% (93.8%–95.1%) | 8.6 | 76.7% |
| 2 | Alex Tosi | 9 | 94.2% (92.9%–95.3%) | 8.7 | 75.0% |
| 3 | Tripp Gibson | 31 | 93.8% (93.1%–94.5%) | 8.7 | 74.7% |
| 4 | Alan Porter | 29 | 93.8% (93.1%–94.5%) | 9.2 | 75.3% |
| 5 | Nic Lentz | 27 | 93.6% (92.8%–94.3%) | 9.4 | 75.3% |
| 6 | Pat Hoberg | 30 | 93.3% (92.6%–94.0%) | 9.9 | 74.0% |
| 7 | Jeremie Rehak | 30 | 93.3% (92.6%–94.0%) | 9.8 | 73.8% |
| 8 | Jansen Visconti | 30 | 93.3% (92.6%–94.0%) | 10.1 | 75.4% |
| 9 | Ryan Blakney | 31 | 93.3% (92.6%–94.0%) | 10.1 | 75.3% |
| 10 | Edwin Moscoso | 33 | 93.3% (92.5%–93.9%) | 10.7 | 75.1% |

## Least accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 94 | Ed Hickox | 18 | 89.7% (88.5%–90.8%) | 16.2 | 67.2% |
| 93 | Rob Drake | 28 | 90.2% (89.2%–91.1%) | 14.1 | 65.1% |
| 92 | Brian O'Nora | 26 | 90.2% (89.3%–91.1%) | 14.2 | 66.5% |
| 91 | Adrian Johnson | 24 | 90.5% (89.5%–91.4%) | 14.7 | 68.4% |
| 90 | Ron Kulpa | 27 | 90.6% (89.7%–91.4%) | 14.3 | 67.0% |
| 89 | Joe West | 31 | 90.6% (89.7%–91.4%) | 14.5 | 67.4% |
| 88 | Kerwin Danley | 14 | 90.6% (89.3%–91.8%) | 15.0 | 68.3% |
| 87 | Greg Gibson | 30 | 90.8% (89.9%–91.6%) | 14.3 | 69.3% |
| 86 | Laz Diaz | 27 | 90.8% (89.9%–91.7%) | 14.2 | 71.2% |
| 85 | Hunter Wendelstedt | 24 | 90.9% (89.9%–91.7%) | 14.6 | 68.7% |

## Strike-calling tendencies

19 umpires call clearly more strikes than expected and 27 call clearly fewer (95% interval excludes zero).

Most extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Doug Eddings | +4.24 (+3.62 to +4.86) | +2.43 | +4.86 |
| Lance Barrett | +1.95 (+1.34 to +2.55) | +1.00 | +2.45 |
| Bill Miller | +1.81 (+1.17 to +2.46) | +1.58 | +3.45 |
| Brian Gorman | +1.76 (+0.93 to +2.58) | +0.35 | +2.94 |
| Brian O'Nora | +1.71 (+1.02 to +2.39) | +1.10 | +1.88 |

Fewest extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Carlos Torres | -2.33 (-2.95 to -1.71) | -1.49 | -3.14 |
| Edwin Moscoso | -1.83 (-2.40 to -1.26) | -1.55 | -2.25 |
| Ryan Wills | -1.80 (-2.51 to -1.08) | +0.92 | -2.01 |
| Larry Vanover | -1.66 (-2.31 to -1.01) | -0.49 | -0.63 |
| Dan Bellino | -1.59 (-2.21 to -0.97) | -0.39 | -1.12 |

## How to read this

- Accuracy compares each call with the measured zone; a pitch is in if any part of the ball touches it.
- Extra strikes compare each call with what the model expects umpires in general to call for the same pitch, count and batter. Positive means more strikes than the league.
- Ranks near each other are usually not meaningfully different; check whether the intervals overlap.
- This is a consistency audit, not a verdict on any umpire.
