# Challenge advisor, 2026

Trained and validated on 10,572 real ABS challenges (5-fold cross-validation grouped by game).

| Model | AUC | Brier | Log loss | Accuracy |
|---|---|---|---|---|
| Always guess the average (53.8%) | 0.500 | 0.249 | 0.690 | 53.8% |
| Challenge advisor | 0.999 | 0.009 | 0.041 | 99.9% |

## Overturn rate by where the pitch was

| Pitch vs the call | Challenges | Actually overturned | Advisor predicted |
|---|---|---|---|
| Call looks right by 2+ in | 980 | 0.0% (0 of 980) | 0.0% |
| Looks right by 1–2 in | 1,460 | 0.1% (1 of 1,460) | 0.0% |
| Looks right by 0–1 in | 2,442 | 0.0% (1 of 2,442) | 6.4% |
| Looks wrong by 0–1 in | 2,667 | 99.9% (2,664 of 2,667) | 94.0% |
| Looks wrong by 1–2 in | 1,860 | 100.0% (1,860 of 1,860) | 100.0% |
| Looks wrong by 2+ in | 1,163 | 99.7% (1,160 of 1,163) | 100.0% |

## What matters

- Location almost completely decides the outcome: a pitch on the wrong side of the zone for the call is overturned nearly every time, and one on the right side almost never is.
- Catchers' challenges succeed more than batters' at the same location (odds × 1.05); pitchers' (odds × 0.85).

## Missed opportunities

- Umpire misses: 24,134 (9.9 per game); teams challenged 23.6% (5,690 of 24,134).
- Misses by 1+ inch, which the advisor rates as likely overturns: 9,457; challenged 32.0% (3,023 of 9,457).
- Challenges on calls that were right (wasted): 46.2% (4,882 of 10,572).
- Wrong strike threes (a batter rung up on a ball): 1,448; fixed by ABS 44.8% (649 of 1,448).
- Wrong ball fours (a walk on a strike): 851; fixed by ABS 42.3% (360 of 851).

## Teams

Clear misses left = misses of 1+ inch that hurt the team and were not challenged.

| Team | Challenges | Overturned | Clear misses left |
|---|---|---|---|
| CIN | 371 | 61.7% | 269 |
| AZ | 308 | 59.7% | 218 |
| ATH | 375 | 59.7% | 224 |
| CHC | 339 | 58.7% | 189 |
| TEX | 294 | 57.8% | 205 |
| PHI | 333 | 57.4% | 166 |
| DET | 331 | 57.1% | 218 |
| MIA | 401 | 56.6% | 216 |
| KC | 332 | 55.4% | 217 |
| TOR | 341 | 55.1% | 216 |
| BOS | 335 | 54.6% | 229 |
| NYY | 398 | 54.5% | 187 |
| LAD | 311 | 54.3% | 214 |
| MIN | 451 | 54.3% | 209 |
| COL | 386 | 54.1% | 188 |
| LAA | 369 | 53.7% | 219 |
| ATL | 305 | 53.1% | 183 |
| MIL | 381 | 52.8% | 253 |
| TB | 342 | 52.6% | 206 |
| HOU | 385 | 52.2% | 194 |
| SF | 335 | 51.3% | 215 |
| NYM | 384 | 51.3% | 216 |
| SEA | 336 | 50.6% | 207 |
| WSH | 339 | 50.4% | 234 |
| SD | 341 | 50.4% | 213 |
| BAL | 325 | 49.8% | 243 |
| STL | 285 | 49.5% | 208 |
| CWS | 442 | 49.3% | 205 |
| CLE | 340 | 48.8% | 229 |
| PIT | 357 | 46.8% | 244 |

## How to read this

- Location comes from pitch tracking, which players can't see in the moment, so the advisor is an upper bound on good decisions and a post-game guide.
- FairCall's zone agrees with ABS rulings on 99.9% of challenged pitches, so location almost decides the outcome; the useful part is spotting which misses deserved a challenge.
