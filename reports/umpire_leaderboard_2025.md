# Umpire consistency audit, 2025

368,845 taken pitches in 2,430 games. Blocked balls included.
84 of 92 umpires have at least 1,000 calls and are rated. 0 pitches had no umpire listed.

## League

- Accuracy against the measured zone: 92.9% (10.8 missed calls per game)
- Accuracy on close pitches (within 2 inches of the edge): 73.0%
- Extra strikes per 100 pitches: +0.00. This should be close to zero; it checks that the model's expectations are unbiased.
- With two strikes: -0.04; with three balls: +0.09

## Most accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 1 | Edwin Jimenez | 26 | 94.8% (94.1%–95.5%) | 7.6 | 79.3% |
| 2 | Mark Ripperger | 32 | 94.4% (93.7%–95.0%) | 7.9 | 77.7% |
| 3 | Derek Thomas | 25 | 94.4% (93.6%–95.1%) | 8.4 | 77.3% |
| 4 | Dan Merzel | 28 | 94.3% (93.6%–95.0%) | 8.3 | 78.6% |
| 5 | Alan Porter | 31 | 94.2% (93.5%–94.9%) | 8.9 | 77.5% |
| 6 | Alex Tosi | 30 | 94.0% (93.3%–94.7%) | 8.9 | 76.0% |
| 7 | Austin Jones | 29 | 94.0% (93.3%–94.7%) | 9.0 | 76.2% |
| 8 | Quinn Wolcott | 32 | 93.9% (93.2%–94.6%) | 8.9 | 75.2% |
| 9 | Emil Jimenez | 29 | 93.9% (93.1%–94.6%) | 8.9 | 75.7% |
| 10 | John Libka | 31 | 93.9% (93.1%–94.5%) | 9.1 | 74.5% |

## Least accurate

| Rank | Umpire | Games | Accuracy (95% CI) | Missed per game | Close-pitch accuracy |
|---|---|---|---|---|---|
| 84 | Bruce Dreckman | 24 | 90.6% (89.6%–91.5%) | 14.3 | 67.1% |
| 83 | Laz Diaz | 31 | 91.4% (90.6%–92.2%) | 13.0 | 69.3% |
| 82 | CB Bucknor | 28 | 91.4% (90.6%–92.2%) | 13.3 | 70.6% |
| 81 | Andy Fletcher | 29 | 91.5% (90.7%–92.3%) | 13.6 | 68.1% |
| 80 | Jonathan Parra | 8 | 91.8% (90.2%–93.1%) | 13.5 | 66.5% |
| 79 | Ron Kulpa | 23 | 91.8% (90.9%–92.7%) | 12.2 | 70.1% |
| 78 | Carlos Torres | 30 | 91.9% (91.1%–92.7%) | 12.4 | 72.2% |
| 77 | Alfonso Márquez | 31 | 92.0% (91.2%–92.7%) | 12.6 | 71.3% |
| 76 | Adrian Johnson | 32 | 92.0% (91.2%–92.8%) | 12.0 | 71.4% |
| 75 | Marvin Hudson | 26 | 92.1% (91.2%–92.8%) | 12.4 | 70.5% |

## Strike-calling tendencies

23 umpires call clearly more strikes than expected and 24 call clearly fewer (95% interval excludes zero).

Most extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Ron Kulpa | +2.13 (+1.44 to +2.82) | +2.74 | +3.95 |
| Vic Carapazza | +1.84 (+1.26 to +2.42) | +1.37 | +1.25 |
| Mike Muchlinski | +1.67 (+1.08 to +2.26) | +0.45 | +2.66 |
| Gabe Morales | +1.53 (+0.96 to +2.10) | +1.03 | +2.36 |
| Ramon De Jesus | +1.46 (+0.87 to +2.05) | -0.02 | -0.74 |

Fewest extra strikes:

| Umpire | Extra strikes per 100 (95% CI) | With two strikes | With three balls |
|---|---|---|---|
| Willie Traynor | -2.04 (-2.87 to -1.21) | -0.95 | -0.81 |
| Lance Barksdale | -1.97 (-2.53 to -1.40) | -1.53 | -3.88 |
| James Jean | -1.72 (-2.41 to -1.04) | -0.66 | -1.50 |
| Jonathan Parra | -1.53 (-2.64 to -0.43) | -0.00 | -2.25 |
| Nic Lentz | -1.52 (-2.11 to -0.94) | -0.50 | -2.14 |

## How to read this

- Accuracy compares each call with the measured zone; a pitch is in if any part of the ball touches it.
- Extra strikes compare each call with what the model expects umpires in general to call for the same pitch, count and batter. Positive means more strikes than the league.
- Ranks near each other are usually not meaningfully different; check whether the intervals overlap.
- This is a consistency audit, not a verdict on any umpire.
