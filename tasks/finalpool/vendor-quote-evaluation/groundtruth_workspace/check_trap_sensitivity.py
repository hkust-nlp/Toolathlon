#!/usr/bin/env python3
"""Prove that every trap planted in the materials is live.

Re-runs ``derive_groundtruth.evaluate`` once per deliberate mistake listed in
``derive_groundtruth.MISTAKES`` and checks that the mistake changes the award
or at least one vendor's evaluation sheet (total, criteria count, decision or
reasons).  Exits 1 if some mistake leaves the result unchanged, which would
mean the corresponding trap no longer tests anything.

    python check_trap_sensitivity.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from derive_groundtruth import MISTAKES, evaluate, load_materials, table_row  # noqa: E402


def signature(results):
    return {r["code"]: tuple(table_row(r)) for r in results}


def main() -> int:
    rules, quotations, notes = load_materials()
    base_results, base_award = evaluate(rules, quotations, notes)
    base_sig = signature(base_results)
    base_award_code = base_award["code"] if base_award else None

    all_live = True
    print(f"baseline award: {base_award_code}\n")
    for mistake, description in MISTAKES.items():
        results, award = evaluate(rules, quotations, notes, mistakes=frozenset({mistake}))
        sig = signature(results)
        changed = sorted(code for code in sig if sig[code] != base_sig[code])
        award_code = award["code"] if award else None
        live = bool(changed) or award_code != base_award_code
        all_live &= live
        flag = "live" if live else "DEAD"
        award_note = f"award {base_award_code}->{award_code}" if award_code != base_award_code else "award unchanged"
        print(f"[{flag}] {mistake:<26} {award_note:<24} sheets changed: {', '.join(changed) or '-'}")
        print(f"       {description}")
    print("\nall traps live" if all_live else "\nSOME TRAPS ARE DEAD")
    return 0 if all_live else 1


if __name__ == "__main__":
    raise SystemExit(main())
