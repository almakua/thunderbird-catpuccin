#!/usr/bin/env python3
# checks WCAG contrast of the roles from build.py for every flavor
# exits with 1 if any pair falls below its threshold

import sys

from build import checks, contrast, load_config, load_palette, roles


def main():
    accent = load_config()["accent"]
    failures = 0
    for flavor, p in load_palette().items():
        r = roles(p, accent)
        print(f"\n{p['name']} ({accent} accent)")
        for label, fg, bg, minimum in checks(r, p):
            ratio = contrast(fg, bg)
            ok = ratio >= minimum
            failures += not ok
            print(f"  {'ok ' if ok else 'NO '} {ratio:5.2f}:1  (min {minimum:>3}:1)  {label:<32} {fg} on {bg}")
    print(f"\n{'All contrast checks pass.' if not failures else f'{failures} pairs below threshold.'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
