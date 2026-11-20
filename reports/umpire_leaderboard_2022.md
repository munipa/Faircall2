# Umpire consistency audit, 2022

366,941 taken pitches in 2,429 games. Blocked balls included.
90 of 96 umpires have at least 1,000 calls and are rated. 0 pitches had no umpire listed.

## League

- Accuracy against the measured zone: 92.5% (11.3 missed calls per game)
- Accuracy on close pitches (within 2 inches of the edge): 71.7%
- Extra strikes per 100 pitches: -0.00. This should be close to zero; it checks that the model's expectations are unbiased.
- With two strikes: -0.04; with three balls: +0.11

## Most accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 1 | Jeremie Rehak | 26 | 94.3% (93.5%–95.0%) | 8.5 | 77.5% |
| 2 | Pat Hoberg | 29 | 93.8% (93.1%–94.5%) | 9.1 | 74.7% |
| 3 | Tripp Gibson | 31 | 93.8% (93.1%–94.4%) | 9.5 | 73.5% |
| 4 | Shane Livensparger | 36 | 93.6% (92.9%–94.2%) | 9.7 | 74.5% |
| 5 | Will Little | 29 | 93.6% (92.8%–94.3%) | 9.7 | 75.1% |
| 6 | Alex Tosi | 22 | 93.6% (92.7%–94.3%) | 10.2 | 75.4% |
| 7 | Mark Ripperger | 30 | 93.6% (92.8%–94.2%) | 9.7 | 74.5% |
| 8 | Mark Wegner | 22 | 93.6% (92.7%–94.3%) | 10.0 | 75.6% |
| 9 | Dan Bellino | 32 | 93.5% (92.8%–94.2%) | 9.8 | 73.6% |
| 10 | Brock Ballou | 7 | 93.5% (91.8%–94.8%) | 10.3 | 72.0% |

## Least accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 90 | Marty Foster | 11 | 90.3% (88.7%–91.6%) | 14.5 | 69.3% |
| 89 | Rob Drake | 21 | 90.5% (89.5%–91.5%) | 14.3 | 66.9% |
| 88 | CB Bucknor | 30 | 90.7% (89.8%–91.6%) | 13.5 | 68.3% |
| 87 | Ted Barrett | 29 | 90.8% (89.9%–91.6%) | 14.6 | 66.3% |
| 86 | Tom Hallion | 10 | 90.8% (89.3%–92.1%) | 14.4 | 66.9% |
| 85 | Greg Gibson | 10 | 91.0% (89.4%–92.4%) | 12.8 | 71.3% |
| 84 | Jerry Layne | 18 | 91.0% (89.9%–92.0%) | 14.1 | 67.9% |
| 83 | Andy Fletcher | 30 | 91.1% (90.2%–91.9%) | 12.7 | 65.7% |
| 82 | Ed Hickox | 18 | 91.2% (90.1%–92.2%) | 13.9 | 71.4% |
| 81 | Malachi Moore | 25 | 91.2% (90.2%–92.1%) | 12.9 | 69.1% |

## Strike-calling tendencies

16 umpires call clearly more strikes than expected and 26 call clearly fewer (95% interval excludes zero).

Most extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Lance Barrett | +2.99 (+2.36 to +3.62) | +1.08 | +4.13 |
| Phil Cuzzi | +2.15 (+1.55 to +2.76) | +0.67 | +3.34 |
| Brian O'Nora | +1.94 (+1.20 to +2.69) | +0.98 | +0.41 |
| Bill Miller | +1.88 (+1.29 to +2.47) | +0.57 | +1.50 |
| Nick Mahrley | +1.86 (+1.30 to +2.42) | +1.27 | +2.63 |

Fewest extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Alan Porter | -2.49 (-3.11 to -1.87) | -1.68 | -5.20 |
| Carlos Torres | -1.98 (-2.59 to -1.38) | -0.70 | +2.23 |
| Todd Tichenor | -1.76 (-2.42 to -1.10) | -1.07 | -1.75 |
| Alfonso Márquez | -1.71 (-2.34 to -1.08) | -2.26 | -4.10 |
| Edwin Moscoso | -1.56 (-2.12 to -1.01) | -1.14 | -1.62 |

## How to read this

- Accuracy compares each call with the measured zone; a pitch is in if any part of the ball touches it.
- Extra strikes compare each call with what the model expects umpires in general to call for the same pitch, count and batter. Positive means more strikes than the league.
- Ranks near each other are usually not meaningfully different; check whether the intervals overlap.
- This is a consistency audit, not a verdict on any umpire.
