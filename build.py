#!/usr/bin/env python3
# builds the .xpi themes plus userChrome.css and userContent.css into dist/
# reads palette.json and config.json, run it with python3 build.py

import json
import pathlib
import shutil
import string
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
TEMPLATES = ROOT / "templates"
VERSION = "1.0.0"

COLOR_NAMES = [
    "rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach", "yellow",
    "green", "teal", "sky", "sapphire", "blue", "lavender",
    "text", "subtext1", "subtext0", "overlay2", "overlay1", "overlay0",
    "surface2", "surface1", "surface0", "base", "mantle", "crust",
]
ACCENTS = COLOR_NAMES[:14]
DENSITY = {"compact": 0, "normal": 1, "touch": 2}


# color and contrast helpers, WCAG 2.x

def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{round(c):02x}" for c in rgb)


def luminance(color):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in hex_to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, t):
    # mixes a toward b by fraction t, from 0 to 1
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def ensure(fg, bg, minimum, toward):
    # nudges fg toward `toward` in small steps until it reaches the minimum contrast on bg
    # if fg already passes it comes back untouched
    for step in range(0, 101, 2):
        candidate = mix(fg, toward, step / 100)
        if contrast(candidate, bg) >= minimum:
            return candidate
    return toward


# semantic roles

def roles(p, accent):
    # maps the palette to UI roles and makes sure each one hits its minimum contrast
    dark = p["dark"]
    r = {
        "frame": p["crust"],
        "chrome": p["mantle"],
        "content": p["base"],
        "field": p["base"],
        "field_border": p["surface1"],
        "border": p["surface0"],
    }

    # primary text gets AAA (7:1) even on the hardest background
    # when the palette falls short, like Latte on crust, we darken or lighten it just enough
    extreme = "#ffffff" if dark else "#000000"
    hardest = min((p["base"], p["mantle"], p["crust"]), key=lambda bg: contrast(p["text"], bg))
    r["text"] = ensure(p["text"], hardest, 7.0, extreme)

    # hover and unfocused selection backgrounds slide toward base until text stays readable
    # contrast is symmetric, so ensure works fine on backgrounds too
    r["hover"] = ensure(p["surface0"], r["text"], 7.0, p["base"])
    r["selected_unfocused"] = ensure(p["surface1"], r["text"], 4.5, p["base"])

    # secondary text has to read well on base, mantle and crust
    r["secondary"] = ensure(p["subtext1"], hardest, 4.5, r["text"])
    r["muted"] = ensure(p["subtext0"], hardest, 4.5, r["text"])

    # accent used as text, like links and folders with new mail
    r["accent"] = ensure(p[accent], p["base"], 4.5, r["text"])
    r["accent_on_chrome"] = ensure(p[accent], p["mantle"], 4.5, r["text"])

    # selection uses the accent as background and whichever text color contrasts best
    sel_bg = p[accent]
    sel_text = max((p["crust"], p["base"], r["text"]), key=lambda c: contrast(c, sel_bg))
    if contrast(sel_text, sel_bg) < 4.5:
        away = "#000000" if luminance(sel_text) > luminance(sel_bg) else "#ffffff"
        sel_bg = ensure(sel_bg, sel_text, 4.5, away)
    r["sel_bg"], r["sel_text"] = sel_bg, sel_text

    # non text elements like bars, focus rings and quotes need at least 3:1
    r["indicator"] = ensure(p[accent], p["base"], 3.0, r["text"])
    quote_order = ["blue", "mauve", "green", "peach", "teal"]
    for i, name in enumerate(quote_order, 1):
        r[f"quote{i}"] = ensure(p[name], p["base"], 3.0, r["text"])
    r["flagged"] = ensure(p["red"], p["base"], 4.5, r["text"])
    r["new"] = ensure(p["green"], p["mantle"], 4.5, r["text"])

    r["scheme"] = "dark" if dark else "light"
    return r


# pairs checked by contrast_check.py as (label, foreground, background, minimum)
def checks(r, p):
    return [
        ("text on message list/preview", r["text"], r["content"], 7.0),
        ("text on toolbar/folders", r["text"], r["chrome"], 7.0),
        ("text on frame", r["text"], r["frame"], 7.0),
        ("text on hover", r["text"], r["hover"], 7.0),
        ("text on unfocused selection", r["text"], r["selected_unfocused"], 4.5),
        ("text on selection", r["sel_text"], r["sel_bg"], 4.5),
        ("secondary on list", r["secondary"], r["content"], 4.5),
        ("secondary on toolbar", r["secondary"], r["chrome"], 4.5),
        ("muted on list", r["muted"], r["content"], 4.5),
        ("link on preview", r["accent"], r["content"], 4.5),
        ("accent on folders", r["accent_on_chrome"], r["chrome"], 4.5),
        ("folders with new mail", r["new"], r["chrome"], 4.5),
        ("flagged on list", r["flagged"], r["content"], 4.5),
        ("unread bar", r["indicator"], r["content"], 3.0),
        *[(f"quote level {i}", r[f"quote{i}"], r["content"], 3.0) for i in range(1, 6)],
    ]


# output generation

def css_vars(p, r):
    lines = [f"  --ctp-{name}: {p[name]};" for name in COLOR_NAMES]
    lines += [f"  --ctp-role-{key.replace('_', '-')}: {value};"
              for key, value in r.items() if key != "scheme"]
    return "\n".join(lines)


def manifest(flavor, p, r, accent):
    return {
        "manifest_version": 2,
        "name": f"Catppuccin {p['name']} Readable",
        "version": VERSION,
        "description": f"Catppuccin {p['name']}, {accent} accent, tuned for readability.",
        "browser_specific_settings": {
            "gecko": {"id": f"catppuccin-leggibile-{flavor}@almakua", "strict_min_version": "128.0"}
        },
        "theme": {
            "colors": {
                "frame": r["frame"],
                "frame_inactive": r["frame"],
                "tab_background_text": r["text"],
                "tab_text": r["text"],
                "tab_selected": r["content"],
                "tab_line": r["indicator"],
                "tab_loading": r["indicator"],
                "tab_background_separator": p["surface1"],
                "toolbar": r["chrome"],
                "toolbar_text": r["text"],
                "toolbar_top_separator": r["frame"],
                "toolbar_bottom_separator": r["border"],
                "toolbar_vertical_separator": p["surface1"],
                "toolbar_field": r["field"],
                "toolbar_field_text": r["text"],
                "toolbar_field_border": r["field_border"],
                "toolbar_field_focus": r["field"],
                "toolbar_field_text_focus": r["text"],
                "toolbar_field_border_focus": r["indicator"],
                "toolbar_field_highlight": r["sel_bg"],
                "toolbar_field_highlight_text": r["sel_text"],
                "button_background_hover": r["hover"],
                "button_background_active": r["selected_unfocused"],
                "icons": r["text"],
                "icons_attention": r["indicator"],
                "popup": r["content"],
                "popup_text": r["text"],
                "popup_border": p["surface1"],
                "popup_highlight": r["sel_bg"],
                "popup_highlight_text": r["sel_text"],
                "sidebar": r["chrome"],
                "sidebar_text": r["text"],
                "sidebar_border": r["border"],
                "sidebar_highlight": r["sel_bg"],
                "sidebar_highlight_text": r["sel_text"],
                "sidebar_highlight_border": r["sel_bg"],
                "ntp_background": r["content"],
                "ntp_text": r["text"],
            },
            "properties": {
                "color_scheme": r["scheme"],
                "content_color_scheme": r["scheme"],
            },
        },
    }


def render(name, **values):
    template = string.Template((TEMPLATES / name).read_text(encoding="utf-8"))
    return template.substitute(values)


def optional_block(name, enabled):
    return (TEMPLATES / name).read_text(encoding="utf-8") if enabled else ""


def load_config():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    if config["accent"] not in ACCENTS:
        sys.exit(f"config.json: invalid accent '{config['accent']}'. Choose one of: {', '.join(ACCENTS)}")
    if config["density"] not in DENSITY:
        sys.exit(f"config.json: invalid density '{config['density']}'. Choose one of: {', '.join(DENSITY)}")
    return config


def load_palette():
    return json.loads((ROOT / "palette.json").read_text(encoding="utf-8"))


def build():
    config = load_config()
    palette = load_palette()
    accent = config["accent"]

    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()

    for flavor, p in palette.items():
        r = roles(p, accent)
        values = {
            "flavor_name": p["name"],
            "accent_name": accent,
            "vars": css_vars(p, r),
            "scheme": r["scheme"],
            "row_min_height": config["row_min_height"],
        }
        tokens = render("ui-tokens.css.tmpl", **values)

        chrome_dir = DIST / flavor / "chrome"
        chrome_dir.mkdir(parents=True)
        (chrome_dir / "userChrome.css").write_text(
            render("userChrome.css.tmpl", tokens=tokens, **values), encoding="utf-8")
        (chrome_dir / "userContent.css").write_text(
            render("userContent.css.tmpl", tokens=tokens,
                   plain_text=optional_block("plain-text.css.tmpl", config["plain_text_messages"]),
                   force_html=optional_block("force-html.css.tmpl", config["force_html_messages"]),
                   **values),
            encoding="utf-8")

        xpi = DIST / f"catppuccin-{flavor}.xpi"
        with zipfile.ZipFile(xpi, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(manifest(flavor, p, r, accent), indent=2, ensure_ascii=False))

        print(f"  {p['name']:<10} {xpi.relative_to(ROOT)}  +  {chrome_dir.relative_to(ROOT)}/")

    prefs = {
        "toolkit.legacyUserProfileCustomizations.stylesheets": "true",
        "mail.uifontsize": str(config["ui_font_size"]),
        "mail.uidensity": str(DENSITY[config["density"]]),
    }
    (DIST / "user.js").write_text(
        "".join(f'user_pref("{k}", {v});\n' for k, v in prefs.items()), encoding="utf-8")
    print(f"  prefs        {(DIST / 'user.js').relative_to(ROOT)}")


if __name__ == "__main__":
    print("Building Catppuccin themes for Thunderbird…")
    build()
