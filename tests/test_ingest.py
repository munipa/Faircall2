from datetime import date

import pandas as pd

from pipeline.ingest import clean, month_ranges


def test_month_ranges_full_window():
    months = [m for m, _, _ in month_ranges(2023, None, None)]
    assert months == list(range(3, 12))


def test_month_ranges_partial():
    r = list(month_ranges(2023, date(2023, 4, 28), date(2023, 5, 2)))
    assert r == [(4, date(2023, 4, 28), date(2023, 4, 30)),
                 (5, date(2023, 5, 1), date(2023, 5, 2))]


def test_clean_keeps_taken_pitches_and_labels():
    base = dict(game_pk=1, game_type="R", at_bat_number=1, plate_x=0.0, plate_z=2.5,
                sz_top=3.5, sz_bot=1.5)
    df = pd.DataFrame([
        {**base, "pitch_number": 1, "description": "called_strike"},
        {**base, "pitch_number": 2, "description": "ball"},
        {**base, "pitch_number": 3, "description": "swinging_strike"},   # swing: dropped
        {**base, "pitch_number": 4, "description": "ball", "plate_x": None},  # no location: dropped
        {**base, "pitch_number": 1, "description": "called_strike"},     # duplicate: dropped
    ])
    out = clean(df)
    assert out["called_strike"].tolist() == [1, 0]
