<div align="center">

<img src="r2save/assets/emblem_64.png" width="64" alt="">

# Remnant 2 Save Editor

**Analyze and edit Remnant 2 saves: resources, items, archetypes, teleport, Blood Moon, world loot.**

Pure Python · no dependencies · dark Remnant-style GUI + CLI · English / Русский

![Character tab](docs/screenshots/character.png)

</div>

> [!WARNING]
> Unofficial fan tool. **Close the game completely before saving**, keep the automatic backups, and use it in
> solo play. Editing saves is at your own risk.

## Features

| | |
|---|---|
| **Character** | Archetype XP with a "max level" button, overview of power level, trait rank and trait points |
| **Resources** | Scrap, Lumenite, Relic Dust, irons, Blood Moon Essence, DLC alloys… Creates missing resources |
| **Inventory** | Searchable list with categories; stack quantity and upgrade level of weapons, mutators and relic fragments |
| **Add item** | Catalog of ~700 rings, amulets, armor, relics, engrams, mutators, consumables and materials by name, with "where to get it in game" |
| **Teleport** | Pick where the game spawns you on the next load: world stones and checkpoints of the campaign or adventure, with readable names (*World stone · Corrupted Ravager*, *Checkpoint · end*) |
| **Blood Moon** | Make the game roll a Blood Moon on the next zone load, then reset the chance afterwards |
| **World analysis** | Bosses, dungeons, events and item pickups of the current roll, their loot and what you already own; jump straight to the zone |
| **All fields** | Raw editor for any number / bool / string in `profile.sav` and `save_N.sav` |
| **Safety** | Automatic backups, a backup browser with restore, undo (Ctrl+Z), change list, protection against overwriting progress the game saved in the meantime |

<table>
<tr>
<td><img src="docs/screenshots/teleport.png" alt="Teleport"></td>
<td><img src="docs/screenshots/world_analysis.png" alt="World analysis"></td>
</tr>
<tr>
<td align="center">Teleport &amp; Blood Moon</td>
<td align="center">World analysis</td>
</tr>
<tr>
<td colspan="2"><img src="docs/screenshots/add_item.png" alt="Add item"></td>
</tr>
<tr>
<td colspan="2" align="center">Item catalog</td>
</tr>
</table>

## Getting started

**Requirements:** Windows, [Python 3.8+](https://www.python.org/downloads/) (keep the default *tcl/tk* option;
ticking *Add python.exe to PATH* is recommended). Steam version of the game.

1. Download the editor: **Code → Download ZIP** and unpack it, or
   `git clone https://github.com/distrix11/Remnant2Editor.git`.
2. Run **`Start Editor.bat`** (or double-click `Remnant2SaveEditor.pyw`).
   The editor finds `%USERPROFILE%\Saved Games\Remnant2\Steam\<id>\profile.sav` automatically; the world save
   `save_N.sav` of the selected character is opened alongside.
3. **Close Remnant 2**, make your changes, press **Save** (Ctrl+S), then start the game.

Interface language: **RU / EN** buttons in the top-right corner (English by default, the choice is remembered).

## Safety

- **Backups.** Every save first copies the original to `<save folder>\_editor_backups\<file>.<date-time>.sav`.
  **Backups…** lists editor backups and the game's own `.bak1–3` with a summary; **Restore** puts one back
  (the current file is backed up first).
- **Verified writes.** Before writing, the result must decompress to exactly the serialized bytes and re-parse
  identically; the file is replaced atomically. On real saves, parse → write reproduces the decompressed file
  **byte for byte** (`tests/roundtrip.py`).
- **No overwriting fresh progress.** If the game rewrote a file after the editor opened it, saving is refused
  and the editor offers to reload. With no pending edits it re-reads changed files when the window regains focus.
- **Undo.** Every edit can be undone; **Changes (N)** lists pending edits and saving shows the list for confirmation.
- **Game check.** The editor refuses to save while `Remnant2-Win64-Shipping.exe` is running.

## What has been tested in game

| Feature | Tested |
|---|---|
| Archetype XP (0 → level 10) | ✅ |
| Resource amounts, creating a missing resource from scratch | ✅ |
| Weapon upgrade level (power / item level recalculated by the game) | ✅ |
| Teleport, including into an unexplored zone | ✅ |
| Summon Blood Moon | ✅ |
| Adding catalog items (rings, amulets, armor…) | ⚠️ same format as tested resources, not checked in game |
| Trait levels | ⚠️ not checked |

### Known risks

- **Weapons can't be added** (they need ammo and mod data); the catalog does not offer them.
- **Upgrade level above the maximum** (+20 regular, +10 boss weapons): game behaviour unknown.
- **Traits:** exceeding available points may make the game reset the allocation.
- **Teleport** to transitions or unexplored zones can put you behind a fog wall or skip a quest trigger.
  World stones and checkpoints of discovered zones are the safe choice.
- **After a forced Blood Moon** the game keeps the chance at 100 %; press *Reset chance (5%)* (the editor warns you).
- **Steam Cloud:** if Steam ever asks which save to keep, choose the local one.
- A game update may change the save format. The editor then fails to open the file instead of writing anything.

## Command line

```bat
python -m r2save info                                 :: characters and archetypes
python -m r2save currency                             :: all resources
python -m r2save currency scrap 50000                 :: set (creates it if missing)
python -m r2save items nightfall --paths              :: search the inventory
python -m r2save set-qty "relic dust" 999
python -m r2save set-level nightfall 10
python -m r2save archetype medic max                  :: or a number
python -m r2save add-item /Game/.../Ring_X.Ring_X_C --equipment
python -m r2save worlds                               :: worlds and spawn points of the active world
python -m r2save teleport 229 536_Checkpoint          :: spawn there on the next load
python -m r2save bloodmoon --now                      :: roll Blood Moon on the next zone load
python -m r2save backups                              :: editor + game backups
python -m r2save restore "<save folder>\_editor_backups\profile.20261105-163107.sav"
python -m r2save dump "<save folder>\save_0.sav" Quest  :: every field of any .sav
python -m r2save verify "<save folder>\profile.sav"   :: byte-exact round-trip check
```

Options: `--file <profile.sav>`, `--world <save_N.sav>`, `--slot N` (character), `--force` (skip the game check).

## How it works

```
[crc32][size][version=9]  +  zlib chunks (≤128 KiB, 49-byte header, tag 0x222222229E2A83C1)
   └─ FileHeader → PackageVersion → save class → OffsetInfo
      → object data (tagged UE properties, actor components) → objects table → names table
```

`profile.sav` holds the characters; each character's inventory, traits and archetypes live in a nested
`PersistenceBlob` (its own names table and objects). `save_N.sav` holds the worlds: every campaign / adventure
roll is a `PersistenceContainer` of actors — zones with their links (world stones, checkpoints, transitions),
quests (bosses, dungeons, events) and the Blood Moon event state. The editor edits the parsed model and
re-serializes everything, so lengths, offsets, names tables, chunks and the CRC are always recomputed.

<details>
<summary>Project layout</summary>

```
Remnant2SaveEditor.pyw   GUI entry point (Start Editor.bat runs it)
r2save/core.py           save format: compression, SaveData, objects, all property types, containers
r2save/nav.py            tree traversal
r2save/profile.py        Profile → Character → Item / Archetype / Trait
r2save/world.py          worlds, zones, spawn points, Blood Moon
r2save/analyzer.py       what is in a rolled world and what is already owned
r2save/itemdb.py         item / event database and localized names
r2save/doc.py            open file + undo history + on-disk change detection
r2save/storage.py        save discovery, backups, restore, verified atomic writes
r2save/gui.py            tkinter GUI          r2save/theme.py   theme, fonts, icons, dialogs
r2save/i18n.py           RU / EN strings      r2save/cli.py     command line
r2save/data/             db.json, names.json (+ their licenses)
r2save/assets/           own icons and emblem, Montserrat font
tests/                   roundtrip.py, edit_test.py, dump.py
tools/make_icons.py      regenerates the icons (needs Pillow)
```

</details>

### Development

```bat
python tests\roundtrip.py "<save folder>\profile.sav" "<save folder>\save_0.sav"   :: read-only
python tests\edit_test.py "<save folder>\profile.sav" "%TEMP%\r2test"               :: edits a copy
pip install pillow && python tools\make_icons.py                                    :: rebuild icons
```

## Credits

- [**lib.remnant2.saves**](https://github.com/AndrewSav/lib.remnant2.saves) by Andrew Savinykh: the save format; `r2save/core.py` is a Python port (MIT).
- [**lib.remnant2.analyzer**](https://github.com/AndrewSav/lib.remnant2.analyzer) by Andrew Savinykh: item and loot database (MIT).
- [**RemnantOverseer**](https://github.com/Angelore/remnant-two-overseer) by Angelore: English / Russian names (MIT).
- [**Montserrat**](https://github.com/JulietaUla/Montserrat): UI font (SIL OFL 1.1).

Details in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

[MIT](LICENSE) © 2026 Dima (distrix11).

Remnant and Remnant II are trademarks of their respective owners. This project is not affiliated with or endorsed
by Gunfire Games or Gearbox Publishing, and contains no game assets.

---

<details>
<summary><b>На русском</b></summary>

**Remnant 2 Save Editor** — неофициальный редактор сохранений Remnant 2: ресурсы, предметы, XP архетипов,
телепорт по камням мира и чекпоинтам, вызов Blood Moon, анализ лута в текущем ролле. Интерфейс на английском
и русском (кнопки RU / EN).

1. Установи [Python 3.8+](https://www.python.org/downloads/).
2. Скачай архив (**Code → Download ZIP**) и запусти `Start Editor.bat`.
3. **Полностью закрой игру**, внеси изменения, нажми **Save** и запусти игру.

Перед каждым сохранением делается бэкап (`_editor_backups` рядом с сейвом), откатить можно кнопкой **Backups…**.
Редактор не даст сохранить, пока запущена игра или если игра успела перезаписать файл. Используй на свой страх и
риск, лучше в соло.

</details>
