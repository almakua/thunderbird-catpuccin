#!/usr/bin/env python3
"""Genera i temi Catppuccin per Thunderbird: .xpi (colori) + userChrome.css + userContent.css.

Uso: python3 build.py            (legge palette.json e config.json, scrive in dist/)
"""

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


# --- Colore e contrasto (WCAG 2.x) -------------------------------------------

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
    """Mescola a verso b di una frazione t (0..1)."""
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)
    return rgb_to_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def ensure(fg, bg, minimum, toward):
    """Restituisce fg, spostandolo verso `toward` a piccoli passi finché non
    raggiunge il contrasto minimo su bg. Se fg passa già, resta invariato."""
    for step in range(0, 101, 2):
        candidate = mix(fg, toward, step / 100)
        if contrast(candidate, bg) >= minimum:
            return candidate
    return toward


# --- Ruoli semantici ---------------------------------------------------------

def roles(p, accent):
    """Mappa la palette su ruoli dell'interfaccia, garantendo i contrasti minimi."""
    dark = p["dark"]
    r = {
        "frame": p["crust"],
        "chrome": p["mantle"],
        "content": p["base"],
        "field": p["base"],
        "field_border": p["surface1"],
        "border": p["surface0"],
    }

    # Testo primario: AAA (7:1) anche sullo sfondo più difficile. Se la palette
    # non basta (Latte su crust), il testo si scurisce/schiarisce quanto serve.
    extreme = "#ffffff" if dark else "#000000"
    hardest = min((p["base"], p["mantle"], p["crust"]), key=lambda bg: contrast(p["text"], bg))
    r["text"] = ensure(p["text"], hardest, 7.0, extreme)

    # Hover e selezione non a fuoco: lo sfondo si avvicina a base finché il testo
    # resta leggibile (contrast è simmetrico, quindi ensure funziona anche sugli sfondi).
    r["hover"] = ensure(p["surface0"], r["text"], 7.0, p["base"])
    r["selected_unfocused"] = ensure(p["surface1"], r["text"], 4.5, p["base"])

    # Il testo secondario deve leggersi sia su base sia su mantle e crust.
    r["secondary"] = ensure(p["subtext1"], hardest, 4.5, r["text"])
    r["muted"] = ensure(p["subtext0"], hardest, 4.5, r["text"])

    # Accento usato come testo (link, nomi di cartelle con messaggi nuovi).
    r["accent"] = ensure(p[accent], p["base"], 4.5, r["text"])
    r["accent_on_chrome"] = ensure(p[accent], p["mantle"], 4.5, r["text"])

    # Selezione: sfondo accento e testo scelto per il massimo contrasto.
    sel_bg = p[accent]
    sel_text = max((p["crust"], p["base"], r["text"]), key=lambda c: contrast(c, sel_bg))
    if contrast(sel_text, sel_bg) < 4.5:
        away = "#000000" if luminance(sel_text) > luminance(sel_bg) else "#ffffff"
        sel_bg = ensure(sel_bg, sel_text, 4.5, away)
    r["sel_bg"], r["sel_text"] = sel_bg, sel_text

    # Elementi non testuali (barre, bordi del focus, citazioni): almeno 3:1.
    r["indicator"] = ensure(p[accent], p["base"], 3.0, r["text"])
    quote_order = ["blue", "mauve", "green", "peach", "teal"]
    for i, name in enumerate(quote_order, 1):
        r[f"quote{i}"] = ensure(p[name], p["base"], 3.0, r["text"])
    r["flagged"] = ensure(p["red"], p["base"], 4.5, r["text"])
    r["new"] = ensure(p["green"], p["mantle"], 4.5, r["text"])

    r["scheme"] = "dark" if dark else "light"
    return r


# Coppie verificate da contrast_check.py: (descrizione, testo, sfondo, minimo).
def checks(r, p):
    return [
        ("testo su elenco/anteprima", r["text"], r["content"], 7.0),
        ("testo su toolbar/cartelle", r["text"], r["chrome"], 7.0),
        ("testo su cornice", r["text"], r["frame"], 7.0),
        ("testo su hover", r["text"], r["hover"], 7.0),
        ("testo su selezione non a fuoco", r["text"], r["selected_unfocused"], 4.5),
        ("testo su selezione", r["sel_text"], r["sel_bg"], 4.5),
        ("secondario su elenco", r["secondary"], r["content"], 4.5),
        ("secondario su toolbar", r["secondary"], r["chrome"], 4.5),
        ("attenuato su elenco", r["muted"], r["content"], 4.5),
        ("link su anteprima", r["accent"], r["content"], 4.5),
        ("accento su cartelle", r["accent_on_chrome"], r["chrome"], 4.5),
        ("cartelle con nuovi", r["new"], r["chrome"], 4.5),
        ("contrassegnato su elenco", r["flagged"], r["content"], 4.5),
        ("barra non letti", r["indicator"], r["content"], 3.0),
        *[(f"citazione livello {i}", r[f"quote{i}"], r["content"], 3.0) for i in range(1, 6)],
    ]


# --- Generazione -------------------------------------------------------------

def css_vars(p, r):
    lines = [f"  --ctp-{name}: {p[name]};" for name in COLOR_NAMES]
    lines += [f"  --ctp-role-{key.replace('_', '-')}: {value};"
              for key, value in r.items() if key != "scheme"]
    return "\n".join(lines)


def manifest(flavor, p, r, accent):
    return {
        "manifest_version": 2,
        "name": f"Catppuccin {p['name']} – Leggibile",
        "version": VERSION,
        "description": f"Catppuccin {p['name']} con accento {accent}, pensato per la leggibilità.",
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
        sys.exit(f"config.json: accento '{config['accent']}' non valido. Scegli tra: {', '.join(ACCENTS)}")
    if config["density"] not in DENSITY:
        sys.exit(f"config.json: densità '{config['density']}' non valida. Scegli tra: {', '.join(DENSITY)}")
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
    print(f"  preferenze   {(DIST / 'user.js').relative_to(ROOT)}")


if __name__ == "__main__":
    print("Generazione temi Catppuccin per Thunderbird…")
    build()
