"""What changed in each version, shown once after an update ("What's new" window) and from the ? window.

Keep it short and player-facing; the full changelog is in README.md. Each entry: version -> (Russian, English)
lists of lines.
"""

NOTES = {
    "1.5.3": (
        [
            "Заставка при запуске с полоской загрузки и анимированным логотипом, плавные переходы между "
            "вкладками. Выключаются в окне «?».",
            "Выбор языка теперь в меню: нажми кнопку языка справа сверху.",
            "Интерфейс на русском помещается в окно: вкладки и колонки больше не обрезаются, а размер окна "
            "подстраивается под масштаб экрана Windows (125 %, 150 %).",
            "Предупреждения внизу вкладок («Телепорт», «Персонаж») снова видны.",
            "После правки таблица остаётся на месте: выделение, прокрутка и сортировка сохраняются.",
            "Окно запоминает размер и положение, открытую вкладку и выбранный мир на «Телепорте» и в «Анализе».",
            "Технические колонки (тип данных, ID) спрятаны за галочкой «Тех. колонки».",
            "Ручное добавление по пути свёрнуто, каталог предметов стал выше.",
            "Доперевод: уровень силы, ранг трейтов, категории инвентаря, названия приключений.",
            "Ctrl+Z и Ctrl+S работают и при русской раскладке.",
            "Исправлено: если один файл записался, а другой нет, «Отменить» больше не падает с ошибкой.",
            "Это окно «Что нового» после каждого обновления (а также кнопка в окне «?»).",
        ],
        [
            "A startup splash with a loading bar and an animated emblem, and smooth tab transitions. They can be "
            "switched off in the ? window.",
            "Language choice is now a menu: click the language button in the top-right corner.",
            "The Russian interface fits the window: tabs and columns are no longer cut off, and the window size "
            "follows the Windows display scaling (125 %, 150 %).",
            "The warnings at the bottom of the Teleport and Character tabs are visible again.",
            "Tables stay where they were after an edit: selection, scroll position and sort order are kept.",
            "The window remembers its size and position, the open tab and the world picked on Teleport and "
            "World analysis.",
            "Technical columns (data type, IDs) are hidden behind the “Technical columns” checkbox.",
            "Manual add by path is folded away, so the item catalog gets more room.",
            "Adventure names are readable (e.g. N'Erud (The Dark Horizon) instead of DLC3_OneShot).",
            "Ctrl+Z and Ctrl+S also work with a non-Latin keyboard layout.",
            "Fixed: when one file was written and the other was not, Undo no longer crashes.",
            "This “What's new” window after every update (also a button in the ? window).",
        ],
    ),
}


def notes(version, lang):
    """Lines for one version in the UI language, or [] if there are none."""
    pair = NOTES.get(version)
    if not pair:
        return []
    return pair[1] if lang == "en" else pair[0]
