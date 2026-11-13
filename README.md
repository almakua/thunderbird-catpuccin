# Catppuccin per Thunderbird – Leggibile

Temi Catppuccin (**Latte, Frappé, Macchiato, Mocha**, gli stessi di [catppuccin/ghostty](https://github.com/catppuccin/ghostty)) per Thunderbird 128+, pensati prima di tutto per la leggibilità.

Sono tre livelli, che si possono usare insieme o separati:

| File | Cosa fa | Installazione |
|---|---|---|
| `dist/catppuccin-<flavor>.xpi` | Colori di cornice, toolbar, cartelle, menu, campi | Componenti aggiuntivi → ⚙ → Installa da file |
| `userChrome.css` | Elenco messaggi, cartelle, intestazioni, focus, contrasti | `./install.sh <flavor>` |
| `userContent.css` | Impostazioni, citazioni, email in testo semplice (opz. HTML) | `./install.sh <flavor>` |

## Installazione

```sh
python3 build.py              # genera dist/
python3 contrast_check.py     # verifica i contrasti WCAG
./install.sh mocha            # o latte | frappe | macchiato  [--profile <percorso>]
```

Poi installa `dist/catppuccin-mocha.xpi` da Thunderbird e riavvia. Per cambiare flavor: rilancia `install.sh` con il nuovo flavor e attiva il tema corrispondente (i 4 `.xpi` possono restare installati insieme).

`install.sh` fa un backup dei file che sovrascrive (`*.bak-<data>`) e aggiunge a `user.js`:
- `toolkit.legacyUserProfileCustomizations.stylesheets = true`, che abilita i CSS;
- `mail.uifontsize` e `mail.uidensity`, cioè la dimensione del testo e la densità dell'interfaccia.

## Scelte per la leggibilità

- **Contrasti garantiti**: testo primario ≥ 7:1 (AAA) su ogni sfondo, testo secondario, link e selezione ≥ 4.5:1, indicatori ≥ 3:1. Se un colore della palette non basta, `build.py` lo sposta di quanto serve: in Latte, per esempio, il testo è leggermente più scuro di `#4c4f69`.
- **Gerarchia degli sfondi**: `crust` per la cornice, `mantle` per toolbar e cartelle, `base` per elenco e lettura.
- **Non letti**: grassetto più una barra accento a sinistra, riconoscibili anche senza distinguere i colori.
- **Selezione**: sfondo accento pieno quando l'elenco ha il focus, grigio (`surface1`) quando non ce l'ha.
- **Elenco messaggi**: righe più alte, separatori tra le righe, date in testo secondario.
- **Intestazione**: oggetto più grande, etichette senza trasparenza.
- **Citazioni**: bordo di 3px, un colore per livello.
- **Firme**: colore attenuato invece dell'opacità al 60%.

## Configurazione (`config.json`)

| Chiave | Default | Valori |
|---|---|---|
| `accent` | `blue` | uno dei 14 accenti Catppuccin (`mauve`, `lavender`, `teal`, …) |
| `ui_font_size` | `14` | px; `0` = default di Thunderbird |
| `density` | `normal` | `compact`, `normal`, `touch` |
| `row_min_height` | `30` | altezza minima delle righe in px |
| `plain_text_messages` | `true` | colori della palette per le email in testo semplice |
| `force_html_messages` | `false` | forza la palette anche sulle email HTML (**invasivo**: newsletter e loghi possono rovinarsi) |

Dopo ogni modifica: `python3 build.py && ./install.sh <flavor>`.

> In alternativa a `force_html_messages`, Thunderbird ha un'impostazione nativa per mostrare le email in modo scuro: `mail.dark-reader.enabled`.

## Struttura

- `palette.json`: i 26 colori di ogni flavor (valori ufficiali Catppuccin).
- `build.py`: definisce i ruoli semantici, i controlli di contrasto e genera `dist/`.
- `templates/`: i sorgenti CSS. I file in `dist/` sono generati, non vanno modificati a mano.
- Il tema si aggancia alle variabili di design di Thunderbird (`--layout-*`, `--tree-*`, `--listbox-*`, `--treeitem-*`, `--folderpane-*`) invece di inseguire i selettori. È verificato su Thunderbird 159.
