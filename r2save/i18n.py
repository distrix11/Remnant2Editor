"""UI strings (Russian / English) and the persisted language setting."""

LANGS = ("ru", "en")
_lang = "en"


S = {
    # toolbar
    "open": ("Открыть…", "Open…"),
    "reload": ("Перечитать", "Reload"),
    "save": ("Сохранить", "Save"),
    "backups": ("Бэкапы…", "Backups…"),
    "character": ("Персонаж:", "Character:"),
    "no_file": ("файл не открыт", "no file opened"),
    "slot": ("слот %d: %s / %s, PL %s", "slot %d: %s / %s, PL %s"),
    # tabs
    "tab_char": ("Персонаж", "Character"),
    "tab_res": ("Ресурсы", "Resources"),
    "tab_inv": ("Инвентарь", "Inventory"),
    "tab_traits": ("Трейты", "Traits"),
    "tab_add": ("Добавить предмет", "Add item"),
    "tab_raw": ("Все поля", "All fields"),
    # overview
    "archetypes_hdr": ("АРХЕТИПЫ", "ARCHETYPES"),
    "col_arch": ("Архетип", "Archetype"),
    "col_level": ("Уровень", "Level"),
    "col_equipped": ("Экипирован", "Equipped"),
    "set_xp": ("Задать XP…", "Set XP…"),
    "max_level": ("Макс. уровень (10)", "Max level (10)"),
    "arch_note": ("Уровень архетипа игра пересчитывает из XP — после сохранения зайди в игру и убей любого врага.\n"
                  "Очки трейтов привязаны к общему уровню персонажа, их XP архетипа не даёт.",
                  "The game recalculates the archetype level from XP — after saving, load in and kill any enemy.\n"
                  "Trait points come from the overall character level, not from archetype XP."),
    "overview": ("Архетипы: %s / %s\nPower level: %s    Item level: %s\nTrait rank: %s    Очки трейтов: %s\n"
                 "Опыт персонажа: %s",
                 "Archetypes: %s / %s\nPower level: %s    Item level: %s\nTrait rank: %s    Trait points: %s\n"
                 "Character XP: %s"),
    "primary": ("основной", "primary"),
    "secondary": ("второй", "secondary"),
    # resources
    "col_res": ("Ресурс", "Resource"),
    "col_qty": ("Количество", "Quantity"),
    "edit": ("Изменить…", "Edit…"),
    "res_note": ("Если ресурса нет в инвентаре («—»), он будет создан. Corrupted Shard игра ограничивает 10 шт.",
                 "If a resource is missing («—») it will be created. The game caps Corrupted Shards at 10."),
    # inventory
    "search": ("Поиск:", "Search:"),
    "category": ("Категория:", "Category:"),
    "all": ("(все)", "(all)"),
    "count": ("%d шт.", "%d items"),
    "col_item": ("Предмет", "Item"),
    "col_cat": ("Категория", "Category"),
    "col_type": ("Тип данных", "Data type"),
    "col_qty_s": ("Кол-во", "Qty"),
    "qty_btn": ("Количество…", "Quantity…"),
    "level_btn": ("Уровень улучшения…", "Upgrade level…"),
    # traits
    "col_trait": ("Трейт", "Trait"),
    "col_kind": ("Вид", "Kind"),
    "trait_level_btn": ("Уровень…", "Level…"),
    "traits_note": ("Осторожно: сумма уровней не должна превышать доступные очки трейтов, иначе игра может "
                    "сбросить распределение. Архетипные трейты (perk) управляются игрой — их лучше не трогать.",
                    "Careful: the total must not exceed your available trait points, or the game may reset the "
                    "allocation. Archetype perks are managed by the game — better leave them alone."),
    "tr_budget": ("Очки трейтов: потрачено %d из %d · свободно %d. Архетипные трейты и перки бесплатные (серые).",
                  "Trait points: %d of %d spent · %d free. Archetype traits and perks are free (grey)."),
    "tr_budget_over": ("⚠ Очки трейтов: потрачено %d из %d — перерасход %d. Игра может сбросить распределение.",
                       "⚠ Trait points: %d of %d spent — %d over. The game may reset the allocation."),
    "tr_budget_unknown": ("Очки трейтов: потрачено %d (сколько доступно — в сейве не найдено)",
                          "Trait points: %d spent (available amount not found in the save)"),
    "tr_over_confirm": ("%s: после изменения будет потрачено %d очков при доступных %d.\n"
                        "Игра может сбросить распределение трейтов. Всё равно изменить?",
                        "%s: after this change %d points would be spent out of %d available.\n"
                        "The game may reset the trait allocation. Change anyway?"),
    "tr_over_save": ("Потрачено %d очков трейтов при доступных %d. Игра может сбросить распределение.\n"
                     "Всё равно сохранить?", "%d trait points are spent out of %d available. The game may reset "
                     "the allocation.\nSave anyway?"),
    "kind_core": ("базовый", "core"),
    "kind_trait": ("обычный", "regular"),
    "kind_archetype": ("архетип", "archetype"),
    "kind_perk": ("перк архетипа", "archetype perk"),
    # add item
    "bp_path": ("Путь блюпринта (например /Game/World_Base/Items/Materials/Scraps/Material_Scraps."
                "Material_Scraps_C):",
                "Blueprint path (e.g. /Game/World_Base/Items/Materials/Scraps/Material_Scraps.Material_Scraps_C):"),
    "kind_material": ("Материал / расходник (есть количество)", "Material / consumable (has a quantity)"),
    "kind_equipment": ("Кольцо / амулет / броня (без количества)", "Ring / amulet / armor (no quantity)"),
    "quantity": ("Количество:", "Quantity:"),
    "add": ("Добавить", "Add"),
    "add_warn": ("Экспериментально. Оружие так не добавляй — ему нужны данные патронов и модов.\n"
                 "Неверный путь = предмет-пустышка, который игра может выкинуть или на котором может упасть. "
                 "Бэкап делается автоматически.",
                 "Experimental. Don't add weapons this way — they need ammo and mod data.\n"
                 "A wrong path creates a dummy item the game may delete or crash on. "
                 "A backup is made automatically."),
    # raw
    "path_filter": ("Фильтр по пути:", "Path filter:"),
    "find": ("Найти", "Find"),
    "col_path": ("Путь", "Path"),
    "col_type_s": ("Тип", "Type"),
    "col_value": ("Значение", "Value"),
    "raw_note": ("Прямое редактирование любых числовых/логических/строковых полей. Работает и для save_0.sav.\n"
                 "Ты сам отвечаешь за смысл значений.",
                 "Direct editing of any numeric/boolean/string field. Works for save_0.sav too.\n"
                 "You are responsible for what the values mean."),
    "matches": ("%d совпадений", "%d matches"),
    "matches_cut": (" (показаны первые %d — уточни фильтр)", " (showing first %d — narrow the filter)"),
    # teleport
    "tab_tp": ("Телепорт", "Teleport"),
    "world": ("Мир:", "World:"),
    "active_mark": (" (активный)", " (active)"),
    "campaign": ("Кампания", "Campaign"),
    "show_unvisited": ("Неисследованные зоны", "Unexplored zones"),
    "show_links": ("Переходы между зонами", "Zone transitions"),
    "tp_info": ("Загрузка сейчас:  %s\nПосле смерти:       %s", "Loads into now:   %s\nAfter death:         %s"),
    "col_zone": ("Зона", "Zone"),
    "col_point": ("Точка", "Point"),
    "col_open": ("Открыта", "Discovered"),
    "type_Waypoint": ("Камень мира", "World stone"),
    "type_Checkpoint": ("Чекпоинт", "Checkpoint"),
    "type_Link": ("Переход", "Transition"),
    "tp_btn": ("Телепорт сюда", "Teleport here"),
    "tp_note": ("Как пользоваться: закрой игру → выбери точку → «Телепорт сюда» → «Сохранить» → загрузись.\n"
                "Безопаснее всего камни мира и чекпоинты в уже открытых зонах.",
                "How to use: close the game → pick a point → «Teleport here» → «Save» → load in.\n"
                "World stones and checkpoints in discovered zones are the safest."),
    "tp_warn": ("⚠ Неоткрытые камни мира (⚠ в таблице) могут дать чёрный экран. Переходы и неисследованные зоны — на свой "
                "риск: можно появиться за туманной стеной или пропустить триггер квеста. Игра должна быть закрыта "
                "полностью — выход в меню не подходит. Бэкап делается автоматически.",
                "⚠ Undiscovered world stones (⚠ in the table) may give a black screen. Transitions and unexplored zones are at "
                "your own risk: you may spawn behind a fog wall or skip a quest trigger. The game must be fully "
                "closed — quitting to the main menu is not enough. A backup is made automatically."),
    "bm_info": ("Blood Moon:  шанс %s%% · последняя проверка %s · последний раз был %s",
                "Blood Moon:  chance %s%% · last check %s · last occurred %s"),
    "bm_none": ("Blood Moon: в этом мире события нет (оно бывает только в Yaesha)",
                "Blood Moon: this world has no such event (Yaesha only)"),
    "bm_btn": ("Вызвать Blood Moon", "Summon Blood Moon"),
    "bm_confirm": ("Шанс Blood Moon станет 100%, а время последней проверки сдвинется на сутки назад.\n"
                   "Игра сама запустит событие при ближайшей загрузке зоны в этом мире, сама его закончит "
                   "и сама сбросит шанс.\nПродолжить?",
                   "The Blood Moon chance becomes 100% and the last check time moves one day back.\n"
                   "The game itself starts the event on the next zone load in this world, ends it and "
                   "resets the chance.\nContinue?"),
    "bm_done": ("Blood Moon подготовлен: 100% при следующей загрузке зоны", "Blood Moon prepared: 100% on the next zone load"),
    "tp_pick": ("Выбери точку в таблице", "Select a point in the table"),
    "tp_confirm_risky": ("%s — %s.\nЭто не открытый камень мира/чекпоинт, возможен черный экран или поломка квеста.\n"
                         "Всё равно телепортировать?",
                         "%s — %s.\nThis is not a discovered world stone/checkpoint; a black screen or a broken quest "
                         "is possible.\nTeleport anyway?"),
    "tp_confirm_stone": ("%s — %s.\n\nЭтот камень мира ещё не открыт. В игре проверено два таких случая: "
                         "Mournful Promenade (зона уже посещена) дал чёрный экран при загрузке, The Great Hall "
                         "(зона ещё не посещена) сработал. Закономерность пока неясна.\n\nБэкап сделается "
                         "автоматически; при чёрном экране закрой игру через диспетчер задач и восстанови его.\n\n"
                         "Телепортировать?",
                         "%s — %s.\n\nThis world stone has not been discovered yet. Two such cases were tested in "
                         "game: Mournful Promenade (zone already visited) gave a black screen on load, The Great Hall "
                         "(zone not visited yet) worked. The pattern is not clear yet.\n\nA backup is made "
                         "automatically; on a black screen kill the game in Task Manager and restore it.\n\n"
                         "Teleport?"),
    "tp_confirm_world": ("Сейчас активен другой мир. %s станет активным — игра загрузит его. Продолжить?",
                         "Another world is active. %s will become the active world — the game will load it. Continue?"),
    "tp_done": ("Телепорт: %s · %s", "Teleport: %s · %s"),
    "risky": ("рискованная точка", "risky point"),
    "no_world": ("Файл мира save_%d.sav не найден рядом с profile.sav", "World file save_%d.sav not found next to profile.sav"),
    "world_dirty": ("Есть несохранённый телепорт. Отбросить его?", "There is an unsaved teleport. Discard it?"),
    # undo / changes / stale
    "changes": ("Изменения (%d)", "Changes (%d)"),
    "undo": ("Отменить", "Undo"),
    "changes_title": ("Несохранённые изменения", "Unsaved changes"),
    "no_changes_yet": ("Изменений пока нет", "No changes yet"),
    "undo_last": ("Отменить последнее", "Undo last"),
    "undo_all": ("Отменить все", "Undo all"),
    "close": ("Закрыть", "Close"),
    "undone": ("Отменено: %s", "Undone: %s"),
    "nothing_to_undo": ("Отменять нечего", "Nothing to undo"),
    "nothing_to_save": ("Изменений нет — сохранять нечего.", "No changes — nothing to save."),
    "save_confirm": ("Записать изменения (%d)?\n\n%s", "Write %d change(s)?\n\n%s"),
    "stale_save": ("%s изменился на диске после открытия — скорее всего, его записала игра.\n"
                   "Сохранение отменено, чтобы не откатить твой прогресс.\n\n"
                   "Перечитать файлы сейчас? Несохранённые правки (%d) будут потеряны, их придётся повторить.",
                   "%s changed on disk after it was opened — most likely the game saved it.\n"
                   "Saving was cancelled so your progress is not rolled back.\n\n"
                   "Reload the files now? Unsaved edits (%d) will be lost and must be redone."),
    "stale_status": ("⚠ %s изменён игрой после открытия — сохранить нельзя, нажми «Перечитать»",
                     "⚠ %s was changed by the game after opening — can't save, press «Reload»"),
    "auto_reloaded": ("%s обновлён игрой — данные перечитаны", "%s was updated by the game — reloaded"),
    "col_file": ("Файл", "File"),
    "col_change": ("Изменение", "Change"),
    # backups
    "bk_title": ("Бэкапы", "Backups"),
    "col_source": ("Источник", "Source"),
    "col_date": ("Дата", "Date"),
    "col_size": ("Размер", "Size"),
    "src_editor": ("редактор", "editor"),
    "src_game": ("игра", "game"),
    "restore_btn": ("Восстановить", "Restore"),
    "open_folder": ("Открыть папку", "Open folder"),
    "bk_restore_confirm": ("Заменить %s бэкапом от %s?\nТекущий файл сначала сохранится в бэкапы.",
                           "Replace %s with the backup from %s?\nThe current file is backed up first."),
    "bk_unsaved_note": ("\n\nНесохранённые правки в редакторе (%d) будут потеряны.",
                        "\n\nUnsaved edits in the editor (%d) will be lost."),
    "bk_restored": ("Восстановлено: %s\nиз %s\n\nПрежний файл сохранён:\n%s",
                    "Restored: %s\nfrom %s\n\nThe previous file was saved to:\n%s"),
    "bk_details_profile": ("Персонажей: %d · активный: %s", "Characters: %d · active: %s"),
    "bk_details_world": ("Активный мир: %s · загрузка: %s · наиграно %.1f ч",
                         "Active world: %s · loads into: %s · played %.1f h"),
    "bk_keep": ("Хранить бэкапов на файл:", "Backups to keep per file:"),
    "bk_keep_all": ("все", "all"),
    "bk_pruned": ("Удалено старых бэкапов: %d", "Old backups removed: %d"),
    "bk_none": ("Бэкапов пока нет", "No backups yet"),
    "bk_note": ("Бэкапы редактора делаются перед каждым сохранением и восстановлением; самые старые удаляются "
                "сверх заданного количества. Файлы .bak1–3 — собственные бэкапы игры, их редактор не трогает.",
                "Editor backups are made before every save and restore; the oldest beyond the chosen number are "
                "removed. .bak1–3 are the game's own backups, the editor never touches them."),
    # blood moon reset
    "bm_reset_btn": ("Сбросить шанс (5%)", "Reset chance (5%)"),
    "bm_stuck": ("⚠ Событие уже было, а шанс остался 100% — нажми «Сбросить шанс», иначе Blood Moon будет "
                 "почти на каждой проверке", "⚠ The event already happened but the chance stayed at 100% — press "
                 "«Reset chance» or Blood Moon will fire on almost every check"),
    "bm_reset_done": ("Шанс Blood Moon сброшен на 5%", "Blood Moon chance reset to 5%"),
    # teleport names
    "col_id": ("ID", "ID"),
    "hint_Start": ("начало", "start"), "hint_End": ("конец", "end"), "hint_Mid": ("середина", "middle"),
    "hint_Final": ("финал", "final"), "hint_Town": ("город", "town"), "hint_POI": ("у объекта", "at POI"),
    "hint_Parent": ("выход наружу", "exit outside"), "hint_Child": ("вход", "entrance"), "hint_Exit": ("выход", "exit"),
    "hint_Zone": ("зона", "zone"), "hint_Dungeon": ("данж", "dungeon"), "hint_Overworld": ("поверхность", "overworld"),
    "hint_Trans": ("переход", "transition"),
    # analysis
    "tab_an": ("Анализ мира", "World analysis"),
    "only_missing": ("Только с недостающим лутом", "Only with missing loot"),
    "col_what": ("Что", "What"),
    "col_where": ("Где", "Where"),
    "col_state": ("Статус", "Status"),
    "col_loot": ("Лут", "Loot"),
    "state_done": ("пройдено", "done"),
    "owned": ("✓ есть", "✓ owned"),
    "missing": ("✗ нет", "✗ missing"),
    "an_summary": ("В ролле: %d записей · не хватает предметов: %d", "In this roll: %d entries · missing items: %d"),
    "an_boss": ("Босс", "Boss"), "an_miniboss": ("Мини-босс", "Mini-boss"), "an_dungeon": ("Данж", "Dungeon"),
    "an_overworld_POI": ("Точка интереса", "Point of interest"), "an_injectable": ("Событие зоны", "Zone event"),
    "an_location": ("Лут локации", "Location loot"), "an_item": ("Предмет", "Item"), "an_event": ("Событие", "Event"),
    "an_story": ("Сюжет", "Story"), "an_trait": ("Книга трейта", "Trait book"),
    "an_note": ("Лут — из базы lib.remnant2.analyzer (AndrewSav), русские названия — из RemnantOverseer (Angelore). «Есть» — предмет уже в инвентаре "
                "выбранного персонажа.", "Loot comes from lib.remnant2.analyzer (AndrewSav), localized names from RemnantOverseer (Angelore). "
                "«Owned» means the item is already in the selected character's inventory."),
    "an_to_tp": ("Телепорт в эту зону…", "Teleport to this zone…"),
    "an_no_zone": ("У этой записи нет зоны", "This entry has no zone"),
    # catalog
    "item_type": ("Тип:", "Type:"),
    "hide_owned": ("Скрыть то, что уже есть", "Hide owned"),
    "col_world": ("Мир", "World"),
    "col_have": ("Есть", "Owned"),
    "add_selected": ("Добавить выбранное", "Add selected"),
    "manual_hdr": ("ВРУЧНУЮ ПО ПУТИ (для опытных)", "MANUAL BY PATH (advanced)"),
    "where_get": ("Где взять в игре: %s", "Where to get it in game: %s"),
    "already_have": ("%s уже есть в инвентаре — количество меняется во вкладке «Инвентарь»",
                     "%s is already in the inventory — change the quantity in the «Inventory» tab"),
    "pick_item": ("Выбери предмет в таблице", "Select an item in the table"),
    "catalog_note": ("Оружие, моды, фрагменты реликвий и навыки отсюда не добавляются — игре нужны для них "
                     "дополнительные данные.", "Weapons, mods, relic fragments and skills can't be added here — "
                     "the game needs extra data for them."),
    "itype_ring": ("Кольцо", "Ring"), "itype_amulet": ("Амулет", "Amulet"), "itype_armor": ("Броня", "Armor"),
    "itype_relic": ("Реликвия", "Relic"), "itype_engram": ("Энграмма", "Engram"),
    "itype_consumable": ("Расходник", "Consumable"), "itype_concoction": ("Настойка", "Concoction"),
    "itype_currency": ("Валюта", "Currency"), "itype_material": ("Материал", "Material"),
    "itype_mutator": ("Мутатор", "Mutator"),
    "itype_weapon": ("Оружие", "Weapon"), "itype_mod": ("Мод", "Mod"), "itype_fragment": ("Фрагмент", "Fragment"),
    "itype_armorspecial": ("Броня", "Armor"), "itype_specialmod": ("Мод", "Mod"), "itype_prism": ("Призма", "Prism"),
    "itype_dream": ("Сон", "Dream"),
    "raw_source": ("Файл:", "File:"),
    # inventory: delete
    "del_btn": ("Удалить…", "Delete…"),
    "del_confirm": ("Удалить «%s» из инвентаря?\n\nОтменить можно через «Отменить» до сохранения, а кольца, амулеты, "
                    "броню, мутаторы, расходники и материалы — вернуть через вкладку «Добавить».",
                    "Remove “%s” from the inventory?\n\nUntil you save, Undo brings it back; rings, amulets, armor, "
                    "mutators, consumables and materials can also be re-added from the Add tab."),
    "del_change": ("Удалён: %s", "Deleted: %s"),
    "del_blocked": ("«%s» нельзя удалить:", "“%s” can't be deleted:"),
    "del_why_type": ("этот вид предметов (%s) редактор не удаляет — оружие, моды, реликвии, фрагменты, предметы "
                     "архетипов, валюты и квестовые предметы связаны с другими данными",
                     "the editor doesn't delete this kind of item (%s) — weapons, mods, relics, fragments, archetype "
                     "items, currencies and quest items are linked to other data"),
    "del_why_equipped": ("он надет (слот %s) — сначала снимите его в игре",
                         "it is equipped (slot %s) — unequip it in the game first"),
    "del_why_attached": ("он вставлен в «%s» — сначала выньте его в игре",
                         "it is attached to “%s” — detach it in the game first"),
    "del_why_mods": ("в нём стоят моды/мутаторы", "it has mods or mutators attached"),
    "del_why_radial": ("он назначен в радиальном меню расходников — уберите его оттуда в игре",
                       "it is bound in the consumables radial menu — unbind it in the game first"),
    # about
    "about_title": ("О программе", "About"),
    "about_version": ("Версия %s", "Version %s"),
    "about_tagline": ("Неофициальный редактор сохранений Remnant 2", "Unofficial save editor for Remnant 2"),
    "about_author": ("АВТОР И ЛИЦЕНЗИЯ", "AUTHOR & LICENSE"),
    "about_credits": ("ИСПОЛЬЗУЕТ", "BUILT ON"),
    "about_files": ("ФАЙЛЫ", "FILES"),
    "about_settings": ("Настройки: %s", "Settings: %s"),
    "about_log": ("Лог ошибок: %s", "Error log: %s"),
    "about_disclaimer": ("Remnant и Remnant II — товарные знаки их владельцев. Проект не связан с Gunfire Games и "
                         "Gearbox Publishing и не содержит файлов игры.",
                         "Remnant and Remnant II are trademarks of their respective owners. This project is not "
                         "affiliated with Gunfire Games or Gearbox Publishing and contains no game assets."),
    # dialogs / messages
    "open_title": ("Открыть сохранение", "Open save"),
    "all_files": ("Все файлы", "All files"),
    "read_fail": ("Не удалось прочитать файл:\n%s\n\n%s", "Could not read the file:\n%s\n\n%s"),
    "loaded": ("Загружено: %s (%d объектов)", "Loaded: %s (%d objects)"),
    "unsaved": ("не сохранено", "not saved"),
    "pick_arch": ("Выбери архетип в таблице", "Select an archetype in the table"),
    "arch_xp_title": ("XP архетипа", "Archetype XP"),
    "arch_xp_prompt": ("%s: новое значение XP\n%d = 10 уровень", "%s: new XP value\n%d = level 10"),
    "new_qty": ("Новое количество", "New quantity"),
    "none": ("нет", "none"),
    "no_instance": ("У предмета нет данных экземпляра", "This item has no instance data"),
    "not_stackable": ("%s — не складываемый предмет (%s). Количество тут скорее всего бессмысленно.\n"
                      "Всё равно изменить?",
                      "%s is not a stackable item (%s). A quantity probably means nothing here.\n"
                      "Change it anyway?"),
    "not_levelable": ("%s не улучшается (тип %s)", "%s cannot be upgraded (type %s)"),
    "level_prompt": ("Уровень улучшения\nОбычное оружие: макс. +20, босс-оружие: +10, мутаторы: 10.\n"
                     "Значение выше максимума игра может обрезать или повести себя странно.",
                     "Upgrade level\nRegular weapons: max +20, boss weapons: +10, mutators: 10.\n"
                     "Above the maximum the game may clamp it or behave oddly."),
    "trait_prompt": ("Уровень трейта", "Trait level"),
    "qty_int": ("Количество — целое число ≥ 1", "Quantity must be a whole number ≥ 1"),
    "added": ("Добавлено: %s", "Added: %s"),
    "not_editable": ("Тип %s здесь не редактируется", "Type %s can't be edited here"),
    "no_changes": ("Изменений нет. Всё равно перезаписать файл?", "No changes. Overwrite the file anyway?"),
    "game_running": ("Remnant 2 запущен. Полностью закрой игру и попробуй снова.\n"
                     "Иначе игра перезапишет файл своими данными.",
                     "Remnant 2 is running. Close the game completely and try again.\n"
                     "Otherwise the game will overwrite the file with its own data."),
    "not_saved": ("Не сохранено:\n%s", "Not saved:\n%s"),
    "saved_status": ("Сохранено. Бэкап: %s", "Saved. Backup: %s"),
    "saved_msg": ("Сохранено.\nБэкап оригинала:\n%s", "Saved.\nBackup of the original:\n%s"),
    "discard": ("Есть несохранённые изменения. Отбросить их?", "You have unsaved changes. Discard them?"),
    # theme dialogs
    "yes": ("Да", "Yes"),
    "no": ("Нет", "No"),
    "cancel": ("Отмена", "Cancel"),
    "need_int": ("Нужно целое число", "A whole number is required"),
    "need_num": ("Нужно число", "A number is required"),
    "range": ("Допустимо: %s … %s", "Allowed: %s … %s"),
}


def t(key, *args):
    pair = S.get(key)
    if pair is None:
        return key
    s = pair[1] if _lang == "en" else pair[0]
    return s % args if args else s


def get_lang():
    return _lang


def set_lang(lang, persist=True):
    global _lang
    if lang not in LANGS:
        return
    _lang = lang
    if persist:
        from . import settings
        settings.set("language", lang)


def load_lang():
    from . import settings
    set_lang(settings.get("language") or "en", persist=False)
    return _lang
