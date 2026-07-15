"""
i18n — Minimal internationalization module.

Usage:
    from i18n import I18n

    i18n = I18n(default='ru')
    i18n.load('translations/ru.json')

    i18n.t('nav.home')  # -> "Главная"
"""
import json
import os
from typing import Any


class I18n:
    def __init__(self, default: str = 'ru'):
        self.default = default
        self.current = default
        self._translations: dict[str, dict[str, Any]] = {}

    def load(self, path: str) -> None:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        lang = data.pop('_lang', os.path.splitext(os.path.basename(path))[0])
        self._translations[lang] = data

    def load_dir(self, directory: str) -> None:
        for name in os.listdir(directory):
            if name.endswith('.json'):
                self.load(os.path.join(directory, name))

    def set_lang(self, lang: str) -> None:
        self.current = lang

    def t(self, key: str, **kwargs) -> str:
        val = self._translations.get(self.current, {})
        for part in key.split('.'):
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
                break
        if val is None:
            val = self._translations.get(self.default, {})
            for part in key.split('.'):
                if isinstance(val, dict):
                    val = val.get(part)
                else:
                    return key
            if val is None:
                return key
        if kwargs:
            try:
                return val.format(**kwargs)
            except (KeyError, IndexError):
                return val
        return val

    def langs(self) -> list[str]:
        return list(self._translations.keys())
