# Catppuccin Readable for Thunderbird

Catppuccin themes for Thunderbird 128 and newer, with the same four flavors you get in [catppuccin/ghostty](https://github.com/catppuccin/ghostty): Latte, Frappé, Macchiato and Mocha. The whole point is readability, so contrast comes first and the palette bends a little when it has to

There are three pieces, and you can use them together or on their own

| File | What it covers | How to install |
|---|---|---|
| `dist/catppuccin-<flavor>.xpi` | frame, toolbars, folder pane, menus, fields | Add-ons and Themes → ⚙ → Install Add-on From File |
| `userChrome.css` | message list, folders, headers, focus, contrast | `./install.sh <flavor>` |
| `userContent.css` | settings pages, quotes, plain text mail and optionally HTML mail | `./install.sh <flavor>` |

## Install

```sh
python3 build.py              # builds everything into dist/
python3 contrast_check.py     # double checks WCAG contrast
./install.sh mocha            # or latte, frappe, macchiato, optionally with --profile <path>
```

Then install the matching `.xpi` and restart Thunderbird. All four themes can stay installed, so switching flavor just means rerunning `install.sh` and enabling the matching theme

`install.sh` finds the profile you actually use through `profiles.ini`, keeps a `*.bak-<date>` copy of anything it overwrites, and sets `toolkit.legacyUserProfileCustomizations.stylesheets`, `mail.uifontsize` and `mail.uidensity` in `user.js`

## What makes it readable

Primary text always gets at least 7:1 contrast, secondary text, links and selection at least 4.5:1, and indicators like bars and focus rings at least 3:1. When a palette color can't make it, `build.py` nudges it just enough, which is why Latte text ends up a touch darker than `#4c4f69`

Surfaces follow a simple hierarchy: `crust` for the frame, `mantle` for toolbars and folders, `base` for the message list and the reading pane

Unread messages are bold and carry an accent bar on the left, so you can spot them without relying on color. The selected row is solid accent while the list has focus and turns `surface1` when it doesn't. Rows are taller, separated by thin lines, and dates sit in secondary text. In the message header the subject is bigger and labels are fully opaque. Quotes get a 3px border with a different color per level, and signatures use a muted color instead of fading out

## Config

Everything lives in `config.json`

| Key | Default | Values |
|---|---|---|
| `accent` | `blue` | any of the 14 Catppuccin accents |
| `ui_font_size` | `14` | in px, `0` keeps the Thunderbird default |
| `density` | `normal` | `compact`, `normal` or `touch` |
| `row_min_height` | `30` | in px |
| `plain_text_messages` | `true` | palette colors for plain text mail |
| `force_html_messages` | `false` | palette colors for HTML mail too, but it's invasive and can wreck newsletters and logos |

After any change run `python3 build.py && ./install.sh <flavor>`

If you'd rather not force colors on HTML mail, Thunderbird has its own dark reader you can turn on with `mail.dark-reader.enabled`

## How it's put together

`palette.json` holds the official Catppuccin colors, `build.py` turns them into roles with contrast rules and writes the output, and `templates/` has the CSS sources. Don't edit `dist/`, it gets regenerated every time

Instead of chasing selectors, the theme overrides Thunderbird's own design tokens (`--layout-*`, `--tree-*`, `--listbox-*`, `--treeitem-*`, `--folderpane-*`), which holds up much better across updates. It's tested on Thunderbird 159
