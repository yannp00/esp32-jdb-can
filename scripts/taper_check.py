#!/usr/bin/env python3
"""Desk-check for the CCL (charge current limit) taper formula used in
jbd-can-vecan.yaml's 0x351 frame. Run this whenever cell_taper_start_v,
cell_taper_end_v, or the taper formula itself changes, to catch arithmetic
errors before transcribing to the embedded C++ lambda.
"""


def ccl(max_cell_v, taper_start, taper_end, current_limit, charge_alarm):
    if charge_alarm:
        return 0.0
    ratio = (taper_end - max_cell_v) / (taper_end - taper_start)
    ratio = max(0.0, min(1.0, ratio))
    return current_limit * ratio


if __name__ == "__main__":
    cases = [
        (3.30, False, 50.0),   # below taper start -> full current
        (3.55, False, 25.0),   # midpoint -> half current
        (3.65, False, 0.0),    # at taper end -> zero
        (3.70, False, 0.0),    # past taper end (defensive, clamp) -> zero
        (3.30, True, 0.0),     # alarm active overrides everything -> zero
    ]

    failures = 0
    for max_v, alarm, expected in cases:
        result = ccl(max_v, 3.45, 3.65, 50.0, alarm)
        ok = abs(result - expected) < 0.01
        status = "OK" if ok else "MISMATCH"
        if not ok:
            failures += 1
        print(f"max_cell_v={max_v} alarm={alarm} -> ccl={result:.2f}A (expected {expected}) {status}")

    if failures:
        raise SystemExit(f"{failures} case(s) failed")
    print("All cases OK")
