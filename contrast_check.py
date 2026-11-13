#!/usr/bin/env python3
"""Verifica i contrasti WCAG dei ruoli generati da build.py per ogni flavor.

Uso: python3 contrast_check.py   (esce con codice 1 se una coppia non passa)
"""

import sys

from build import checks, contrast, load_config, load_palette, roles


def main():
    accent = load_config()["accent"]
    failures = 0
    for flavor, p in load_palette().items():
        r = roles(p, accent)
        print(f"\n{p['name']} (accento {accent})")
        for label, fg, bg, minimum in checks(r, p):
            ratio = contrast(fg, bg)
            ok = ratio >= minimum
            failures += not ok
            print(f"  {'ok ' if ok else 'NO '} {ratio:5.2f}:1  (min {minimum:>3}:1)  {label:<32} {fg} su {bg}")
    print(f"\n{'Tutti i contrasti rispettano le soglie.' if not failures else f'{failures} coppie sotto soglia.'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
