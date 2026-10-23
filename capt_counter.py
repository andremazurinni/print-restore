"""
Счётчик напечатанных листов Canon LBP-1120 (30.09.2026).

У принтера нет ни накопительного счётчика, ни индикации тонера (см. память проекта), поэтому
считаем сами: драйвер после каждой успешно отправленной страницы вызывает add_sheet().
Файл C:\\ProgramData\\CaptPrinter\\counter.json читает и обнуляет скрипт printer_counter.ps1.
Модуль без зависимостей от остального драйвера и никогда не бросает исключений наружу:
сбой счётчика не должен ломать печать.
"""
import json
import os
import time

DATA_DIR = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "CaptPrinter")
COUNTER_PATH = os.path.join(DATA_DIR, "counter.json")

# Canon EP-22: до 2500 страниц A4 при 5% заполнения (данные продавцов). Меняется в counter.json
# (поле rated_pages) или скриптом printer_counter.ps1 -Rated N - например, для заправленного картриджа.
DEFAULT_RATED_PAGES = 2500
THRESHOLDS = (80, 95, 100)   # проценты ресурса, при которых показываем уведомление (один раз на картридж)


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _fresh():
    return {
        "version": 1,
        "total": 0,
        "since_cartridge": 0,
        "cartridge_started": _now(),
        "rated_pages": DEFAULT_RATED_PAGES,
        "by_size": {},
        "notified": [],
        "history": [],
        "option_reset_seen": False,
    }


def load(path=None):
    """Читает счётчик; при отсутствии/повреждении файла возвращает чистый (битый файл откладывается в .bad)."""
    path = path or COUNTER_PATH
    try:
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
        base = _fresh()
        base.update({k: v for k, v in d.items() if k in base})
        for k in ("total", "since_cartridge", "rated_pages"):
            base[k] = int(base[k])
        if base["rated_pages"] <= 0:
            base["rated_pages"] = DEFAULT_RATED_PAGES
        if not isinstance(base["by_size"], dict):
            base["by_size"] = {}
        if not isinstance(base["notified"], list):
            base["notified"] = []
        if not isinstance(base["history"], list):
            base["history"] = []
        return base
    except FileNotFoundError:
        return _fresh()
    except Exception:
        try:
            os.replace(path, path + ".bad")
        except OSError:
            pass
        return _fresh()


def _save(d, path=None):
    path = path or COUNTER_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def add_sheet(size_label="A4", path=None):
    """
    +1 лист. Возвращает словарь {"total", "since", "rated", "percent", "crossed": [80|95|100, ...]}
    (crossed - пороги, пройденные ИМЕННО этим листом и ещё не показанные) либо None при сбое.
    """
    try:
        d = load(path)
        d["total"] += 1
        d["since_cartridge"] += 1
        d["by_size"][size_label] = int(d["by_size"].get(size_label, 0)) + 1
        d["last_print"] = _now()
        pct = d["since_cartridge"] * 100.0 / d["rated_pages"]
        crossed = [t for t in THRESHOLDS if pct >= t and t not in d["notified"]]
        d["notified"] = sorted(set(d["notified"]) | set(crossed))
        _save(d, path)
        return {"total": d["total"], "since": d["since_cartridge"], "rated": d["rated_pages"],
                "percent": round(pct, 1), "crossed": crossed}
    except Exception:
        return None


def reset_cartridge(path=None):
    """Замена картриджа: текущие листы уходят в history, счётчик "с последней замены" обнуляется."""
    d = load(path)
    d["history"].append({"from": d["cartridge_started"], "to": _now(), "sheets": d["since_cartridge"],
                         "rated_pages": d["rated_pages"]})
    d["since_cartridge"] = 0
    d["cartridge_started"] = _now()
    d["notified"] = []
    _save(d, path)
    return d


def option_reset(value, path=None):
    """
    Строка "Счётчик картриджа" в окне печати: "replaced" обнуляет счётчик ОДИН раз - пока в заданиях
    остаётся "replaced", повторно не обнуляем (флаг option_reset_seen в файле); "keep" флаг снимает.
    Возвращает True, если счётчик только что обнулён. Никогда не бросает.
    """
    try:
        d = load(path)
        if value == "replaced":
            if d.get("option_reset_seen"):
                return False
            d = reset_cartridge(path)
            d["option_reset_seen"] = True
            _save(d, path)
            return True
        if d.get("option_reset_seen"):
            d["option_reset_seen"] = False
            _save(d, path)
        return False
    except Exception:
        return False
