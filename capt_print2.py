"""
Печать на Canon LBP-1120 через WinUSB, протокол и последовательность команд
портированы НАПРЯМУЮ из оригинального драйвера Nicolas Boichat (2004, LBP-810,
то же поколение движка, что и LBP-1120): http://www.boichat.ch/nicolas/capt/
Файл-первоисточник: capt.c / capt.h из архива capt-0.1.tar.gz

Это не приближение через LBP2900 (как в capt_print.py) - это порт РЕАЛЬНО
работавшего протокола именно для этой линейки принтеров.

Авторство:
  Реверс-инжиниринг протокола Canon CAPT (LBP-810/LBP-1120), 2004:
    (C) Nicolas Boichat <nicolas@boichat.ch>, на базе работы Rildo Pragana
    (драйвер Samsung ML-85G). http://www.boichat.ch/nicolas/capt/
  Порт на Python, интеграция с WinUSB и Ctrl-P (Windows), 2026:
    andre_mazurinni

Лицензия: GNU GPL (унаследована от исходного кода Boichat/Pragana) - см. COPYING.
"""
import os
import sys
import time
import struct
import msvcrt
import usb.core
import usb.util
import libusb_package

VENDOR_ID = 0x04A9
PRODUCT_ID = 0x262B
PRODUCT_ID_810 = 0x260A  # Canon LBP-810 (13.10.2026): включается только явно, CAPT_ENABLE_810=1

LINE_SIZE = 592
LINES_BY_PAGE = 6968
ROWS_BY_BAND = 104
# Родной драйвер Canon (USB-дампы 24.09.2026) никогда не шлёт кусок данных больше
# ~32 КБ (max 32288 из 5 дампов, включая страницу в 2 МБ) - при том что "буфер" в
# статусе принтера считается блоками по 32 КБ. Наши 63-КБ куски, вероятно, и были
# причиной обрыва печати "больше ~512 КБ": принтер сообщает "не полон" при
# свободных <63 КБ. Кодировщик v2 режет поток на куски не больше PACKET_LIMIT.
PACKET_LIMIT = 32000

# ---------------------------------------------------------------------------
# Настройки качества (24.09.2026) - по образцу вкладки Quality родного драйвера.
# Файл C:\ProgramData\CaptPrinter\settings.ini (создаётся с комментариями при
# первом запуске; правится блокнотом, читается при каждой печати). Байты параметров
# страницы (a0d0) взяты из USB-дампов родного драйвера (usb_dumps 08, 13-17).
# ---------------------------------------------------------------------------
SETTINGS_DIR = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "CaptPrinter")
SETTINGS_PATH = os.path.join(SETTINGS_DIR, "settings.ini")
SETTINGS_TEMPLATE = """; Настройки печати Canon LBP-1120 (как вкладка Quality родного драйвера).
; Меняйте значения и сохраняйте файл - действуют со следующего задания. Неверное
; значение игнорируется (берётся стандартное). Строки с ; - комментарии.
[print]
; Разрешение: 600 (по умолчанию, чёткая печать) или 300 (в 3-4 раза меньше данных, быстрее).
resolution = 600
; Плотность тонера: 0 (Light) ... 31 (по умолчанию) ... 63 (Dark). Можно словами: light / normal / dark.
toner_density = 31
; Экономия тонера: 0 - выкл, 1 - вкл.
toner_saver = 0
; Automatic Image Refinement (сглаживание краёв силами принтера): 1 - вкл (по умолчанию), 0 - выкл.
refinement = 1
; Яркость и контраст, проценты от -100 до 100 (0 - без изменений). Применяются к странице до растрирования.
brightness = 0
contrast = 0
; Полутона: auto - как выбрано очередью печати; либо принудительно:
; screen (кластерный экран родного драйвера, Pattern 1), ordered (Байер 4x4),
; floyd-steinberg (плавный, аналог Smooth), threshold (без полутонов).
halftone = auto
; Серийный номер принтера, если к ПК подключены два и более (например 0346C8aT). Пусто -
; печать на первый найденный. Серийный номер виден в диспетчере устройств или на
; метке тест-листа. Если принтер с таким номером не найден, печать отменяется.
printer_serial =
; Компенсация потемнения средних тонов (тонер расплывается вокруг точек, серый 50%
; печатается почти чёрным): 1 - вкл (по умолчанию), 0 - выкл.
tone_correction = 1
; Сила поправки тонов, 0..100 % (по умолчанию 50 - компромисс 05.10.2026: ровные градиенты и
; различимые тёмные тона; 100 - полная поправка, заметна зернистость в тёмных тонах).
tone_strength = 50
; Положение фото на листе при печати через правый клик (Печать через LBP1120):
; по вертикали top (вверху, по умолчанию) / center / bottom,
; по горизонтали center (по центру, по умолчанию) / left / right.
photo_valign = top
photo_halign = center
; Размер фото: full - всегда на весь лист (по умолчанию, решение пользователя 05.10.2026: масштаб не уменьшать;
; плотное фото тогда печатается режимом floyd12 - точка 1x2); shrink - вместо этого уменьшать фото
; шагом 5% (не меньше 50%), пока оно не пройдёт в самом мелком режиме floyd 1x1.
photo_fit = full
; Пропуск пустых страниц: 1 - полностью белые страницы не печатаются (экономит лист и тонер), 0 - печатать все (по умолчанию).
skip_blank_pages = 0
; Сдвиг печати на листе, мм (-10..10): X вправо, Y вниз. Для принтера, который печатает чуть в сторону.
; shift810_* - то же только для LBP-810 (если задано, важнее shift_*).
shift_x_mm = 0
shift_y_mm = 0
shift810_x_mm =
shift810_y_mm =
; Поворот страницы на 180 градусов (бланк или лист лежит в лотке другой стороной): 1 - вкл.
rotate180 = 0
; Весь текст чёрным: 1 - серый текст и линии темнее 160 вне фото печатаются сплошным чёрным (чётче мелкий текст).
text_black = 0
; Коррекция тонких линий: 0 - выкл, 1 - утолщить тонкие тёмные линии и мелкие штрихи на 1 px (0,04 мм) с каждой стороны,
; 2 - на 2 px. Фото не затрагивается.
thin_lines = 0
; Ручной дуплекс (печать на обеих сторонах вручную): 1 - сначала печатаются нечётные страницы, затем окно
; "переверните стопку и положите в лоток", затем чётные. duplex_even_reverse = 1: чётные идут в обратном порядке
; (стопка вышла лицевой стороной вниз); при нечётном числе страниц последний лист получит чистую оборотную сторону.
; duplex_even_rotate = 1 (по умолчанию, проверено на LBP-810 14.10.2026): чётные страницы поворачиваются на 180 градусов;
; стопка переворачивается как страница книги (верх сверху, чистая сторона к себе). 0 - если оборот ложится вверх ногами при другом способе.
manual_duplex = 0
duplex_even_reverse = 1
duplex_even_rotate = 1
; Быстрый набор настроек (идея Quick Print / ярлыков печати Kyocera, HP, Canon): text - чёткий текст и линии,
; photo - плавные полутона (floyd-steinberg), saver - экономия тонера (+ утолщение тонких линий), draft - черновик
; (300 dpi, экономия, светлее). Пусто - без набора. Набор важнее остальных значений этого файла и окна печати;
; для отдельной очереди набор задаётся аргументом порта: --preset photo.
preset =
; Перевод цвета в серый для цветных страниц: classic - по умолчанию (0,299 R + 0,587 G + 0,114 B, как в предпросмотре
; серого); luminance - как у Windows при «Чёрно-белая печать»: световая яркость с гаммой 2,2, насыщенные цвета
; (голубой, малиновый, красный, зелёный) светлее на 20-45 единиц (скан 14.10.2026). Страницы, уже ставшие серыми
; в Windows или в программе, не затрагиваются.
gray_conversion = classic
; Какой принтер печатает картинки по правому клику («Печать через LBP1120»): auto - 1120, а если его нет, то 810;
; 1120 или 810 - всегда указанный (при двух подключённых принтерах).
image_printer = auto
"""

DEFAULT_SETTINGS = {
    "resolution": 600, "toner_density": 31, "toner_saver": 0, "refinement": 1,
    "brightness": 0, "contrast": 0, "halftone": "auto", "tone_correction": 1, "tone_strength": 50, "printer_serial": "", "photo_valign": "top", "photo_halign": "center", "photo_fit": "full",
    "preset": "", "gray_conversion": "classic", "image_printer": "auto", "rotate180": 0, "text_black": 0, "thin_lines": 0, "manual_duplex": 0, "duplex_even_reverse": 1, "duplex_even_rotate": 1,
    "skip_blank_pages": 0, "shift_x_mm": 0.0, "shift_y_mm": 0.0, "shift810_x_mm": None, "shift810_y_mm": None,
}
_HALFTONES = ("auto", "floyd12", "smart", "screen", "ordered", "floyd-steinberg", "threshold")

# Быстрые наборы настроек (13.10.2026): значения ключей settings.ini, накладываются поверх всего остального.
PRESETS = {
    "text": {"halftone": "smart", "text_black": 1, "thin_lines": 1, "toner_saver": 0, "refinement": 1, "tone_correction": 1},
    "photo": {"halftone": "screen", "text_black": 0, "thin_lines": 0, "toner_saver": 0, "refinement": 1,
              "tone_correction": 1, "tone_strength": 50},
    "saver": {"halftone": "auto", "text_black": 1, "thin_lines": 1, "toner_saver": 1, "toner_density": 31},
    "draft": {"halftone": "smart", "resolution": 300, "toner_saver": 1, "toner_density": 15, "thin_lines": 0, "text_black": 0},
}
PRESET_LABELS = {"text": ("Текст", "Text"), "photo": ("Фото", "Photo"), "saver": ("Экономия", "Toner saver"),
                 "draft": ("Черновик", "Draft")}


def apply_preset(settings: dict, name: str, logger=None) -> bool:
    """Накладывает быстрый набор на настройки задания. Неизвестное имя игнорируется (печать идёт как обычно)."""
    name = (name or "").strip().lower()
    if not name:
        return False
    if name not in PRESETS:
        if logger:
            logger(f"  preset = {name!r}: допустимо {tuple(PRESETS)}, игнорирую")
        return False
    settings.update(PRESETS[name])
    if logger:
        logger(f"  Быстрый набор «{name}»: {PRESETS[name]}")
    return True


def load_settings(logger=None):
    """Читает settings.ini; при отсутствии - создаёт шаблон (best-effort). Всегда возвращает
    полный словарь допустимых значений: ошибки в файле не должны ломать печать."""
    import configparser
    s = dict(DEFAULT_SETTINGS)

    def warn(msg):
        if logger:
            logger(f"  settings.ini: {msg}")

    try:
        if not os.path.exists(SETTINGS_PATH):
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                f.write(SETTINGS_TEMPLATE)
            return s
        cp = configparser.ConfigParser(inline_comment_prefixes=(";",))
        cp.read(SETTINGS_PATH, encoding="utf-8-sig")
        sec = cp["print"] if cp.has_section("print") else {}
    except Exception as e:  # noqa: BLE001 - любой сбой чтения = стандартные значения
        warn(f"не удалось прочитать ({e!r}), использую стандартные значения")
        return s

    def get_int(key, lo, hi, allowed=None):
        raw = str(sec.get(key, "")).strip()
        if not raw:
            return
        try:
            v = int(raw)
        except ValueError:
            warn(f"{key} = {raw!r}: не число, игнорирую")
            return
        if allowed is not None and v not in allowed:
            warn(f"{key} = {v}: допустимо {allowed}, игнорирую")
            return
        if not lo <= v <= hi:
            warn(f"{key} = {v}: вне диапазона {lo}..{hi}, игнорирую")
            return
        s[key] = v

    get_int("resolution", 300, 600, allowed=(300, 600))
    raw = str(sec.get("toner_density", "")).strip().lower()
    if raw in ("light", "normal", "dark"):
        s["toner_density"] = {"light": 0, "normal": 31, "dark": 63}[raw]
    else:
        get_int("toner_density", 0, 63)
    get_int("toner_saver", 0, 1)
    get_int("refinement", 0, 1)
    get_int("brightness", -100, 100)
    get_int("contrast", -100, 100)
    get_int("tone_correction", 0, 1)
    get_int("tone_strength", 0, 100)
    get_int("skip_blank_pages", 0, 1)
    s["preset"] = str(sec.get("preset", "")).strip().lower()
    raw = str(sec.get("image_printer", "")).strip().lower()
    if raw:
        if raw in ("auto", "1120", "810"):
            s["image_printer"] = raw
        else:
            warn(f"image_printer = {raw!r}: допустимо auto, 1120 или 810, игнорирую")
    raw = str(sec.get("gray_conversion", "")).strip().lower()
    if raw:
        if raw in ("classic", "luminance"):
            s["gray_conversion"] = raw
        else:
            warn(f"gray_conversion = {raw!r}: допустимо classic или luminance, игнорирую")
    get_int("rotate180", 0, 1)
    get_int("text_black", 0, 1)
    get_int("thin_lines", 0, 2)
    get_int("manual_duplex", 0, 1)
    get_int("duplex_even_reverse", 0, 1)
    get_int("duplex_even_rotate", 0, 1)
    for key in ("shift_x_mm", "shift_y_mm", "shift810_x_mm", "shift810_y_mm"):
        raw = str(sec.get(key, "")).strip().replace(",", ".")
        if not raw:
            continue
        try:
            v = float(raw)
        except ValueError:
            warn(f"{key} = {raw!r}: не число, игнорирую")
            continue
        if not -10.0 <= v <= 10.0:
            warn(f"{key} = {v}: вне диапазона -10..10, игнорирую")
            continue
        s[key] = v
    s["printer_serial"] = str(sec.get("printer_serial", "")).strip()
    for key, allowed in (("photo_valign", ("top", "center", "bottom")), ("photo_halign", ("left", "center", "right")),
                         ("photo_fit", ("shrink", "full"))):
        raw = str(sec.get(key, "")).strip().lower()
        if raw:
            if raw in allowed:
                s[key] = raw
            else:
                warn(f"{key} = {raw!r}: допустимо {allowed}, игнорирую")
    raw = str(sec.get("halftone", "")).strip().lower()
    if raw:
        if raw in _HALFTONES:
            s["halftone"] = raw
        else:
            warn(f"halftone = {raw!r}: допустимо {_HALFTONES}, игнорирую")
    return s


SETTINGS = load_settings()
RESOLUTION_DPI = 600


def apply_resolution(dpi):
    """Переключает геометрию растра: 600 dpi (592 байта/строка) или 300 dpi (296 байт/строка,
    3390 строк в заголовке - по дампу родного драйвера 08_photo_default_300)."""
    global LINE_SIZE, LINES_BY_PAGE, RESOLUTION_DPI
    RESOLUTION_DPI = dpi
    if dpi == 300:
        LINE_SIZE, LINES_BY_PAGE = 296, 3485   # 3485 = 3390 + запас, как 6968 = 6778 + 190 у 600 dpi
    else:
        LINE_SIZE, LINES_BY_PAGE = 592, 6968


# Геометрия бумаги, отличной от A4 (28.09.2026): для A4 используются только проверенные
# байт-в-байт константы из build_pageparms ниже (родной дамп) - _PAGEPARMS_GEOM=None.
# Для любого другого размера (сейчас - A5) геометрия вычисляется по формуле, откалиброванной
# реальной печатью+сканом 28.09.2026 (см. project_lbp1120_usb_capture_plan.md): канва/a0d0
# берутся РОВНО по размеру листа (margin_px=0 в самом протоколе - печать до края подтверждена
# линейкой 2..14мм, ВСЕ рамки целиком, включая 2мм, без запаса по высоте тоже). Видимое поле
# на бумаге (CONTENT_MARGIN_MM) делается отдельно, только при вписывании содержимого в канву
# (capt_print_pdf._render_gray_canvas) - раньше отступ протокола и сжатие контента складывались
# ("двойной отступ", жалоба пользователя), теперь отступ ровно один и настраиваемый.
# Байты [2:8]=dd,00,07,01,00,00 скопированы из реального USB-дампа B5 (единственный известный
# не-A4 дамп родного драйвера) - назначение не разобрано, но работает (проверено печатью A5).
_PAGEPARMS_GEOM = None  # (LINE_SIZE, height_buf_px, paper_w_px, paper_h_px) или None = A4
A4_TRUE_SIZE = False   # True: страница A4 (210x297) печатается 1:1 без вписывания/сжатия (решение 01.10.2026)
CONTENT_MARGIN_MM = 2  # зона у левого/правого/нижнего края листа, где ничего не печатаем (не-A4) - читает capt_print_pdf
TOP_OFFSET_PX = 120    # аппаратный отступ сверху @600 dpi (~5.08 мм), см. apply_paper_geometry


# Единственный сегодня откалиброванный не-A4 размер (29.09.2026, печать+скан). Страница
# PDF-задания может быть ЛЮБОГО размера (например, макет для типографии 300x350мм у
# "Карамель" 29.09.2026 - это НЕ размер бумаги в лотке, а просто размер макета!) - раньше
# такие страницы всегда печатались вписанными в A4, и это должно остаться поведением по
# умолчанию. Автоопределение применяется, только если размер страницы совпадает с одним из
# ИЗВЕСТНЫХ реальных размеров бумаги - иначе результат непредсказуем (баг найден на "Карамель").
_KNOWN_PAPER_SIZES_MM = {"A5": (148.0, 210.0), "A6": (105.0, 148.0), "A7": (74.0, 105.0)}


# Пределы своего размера бумаги (мм, короткая x длинная сторона): по списку размеров родного
# драйвера Canon (Index Card 76x127 - самый маленький) и по проверенному диапазону печати
# (до A4: ширина печатной зоны рассчитана до 210 мм, длина проверена до 297 мм). Legal (356 мм)
# и Letter (216 мм шириной) не проверены - остаются "вписанными в A4".
CUSTOM_SIZE_MIN_MM = (76.0, 127.0)
CUSTOM_SIZE_MAX_MM = (210.5, 297.5)


def _size_label():
    """Размер листа для счётчика: A4 (в т.ч. вписанные в A4 страницы), A5, A6 или свой."""
    if _PAGEPARMS_GEOM is None:
        return "A4"
    w_mm = _PAGEPARMS_GEOM[2] / RESOLUTION_DPI * 25.4
    h_mm = _PAGEPARMS_GEOM[3] / RESOLUTION_DPI * 25.4
    for name, (kw, kh) in _KNOWN_PAPER_SIZES_MM.items():
        if abs(w_mm - kw) < 3 and abs(h_mm - kh) < 3:
            return name
    return "custom"


def _count_sheet(logger=print, is_810=False):
    """+1 лист в счётчике картриджа (capt_counter) и уведомление о ресурсе (80%/95%/100%). Никогда не бросает.
    LBP-810 считается в своём файле counter_810.json (13.10.2026): у него свой картридж, счётчик 1120 не трогаем."""
    try:
        import capt_counter
        path = os.path.join(capt_counter.DATA_DIR, "counter_810.json") if is_810 else None
        r = capt_counter.add_sheet(_size_label(), path)
        if not r:
            return
        logger(f"  счётчик листов: всего {r['total']}, с замены картриджа {r['since']} из ~{r['rated']} ({r['percent']}%)")
        if r["crossed"]:
            t = max(r["crossed"])
            if t >= 100:
                ru = f"Картридж выработал ресурс: напечатано {r['since']} из ~{r['rated']} листов. Замените картридж."
                en = f"Cartridge is at its rated life: {r['since']} of ~{r['rated']} sheets printed. Replace the cartridge."
            else:
                ru = f"Картридж израсходован на ~{t}% ({r['since']} из ~{r['rated']} листов). Подготовьте новый."
                en = f"Cartridge is ~{t}% used ({r['since']} of ~{r['rated']} sheets). Get a new one ready."
            # кнопка обнуления: reset - counter.json (1120), reset810 - counter_810.json (13.10.2026)
            btns = [(tr("Картридж заменён - обнулить", "Cartridge replaced - reset"),
                     "captcounter://reset810" if is_810 else "captcounter://reset"),
                    (tr("Напомнить позже", "Remind me later"), None)]
            notify("Canon LBP-810" if is_810 else "Canon LBP-1120", tr(ru, en), buttons=btns)
    except Exception:
        pass


NATIVE810_MARGIN_PX = 112   # поле слева/справа у родного A4 810 (4,7 мм); у B5 133,5 - для A5/A6/A7 берём как у A4
NATIVE810_HB_CUT = 237      # высота буфера родного драйвера = высота листа - 237 (A4: 6778 из 7015, B5: 5832 из 6070)


def native810_geom():
    """Не-A4 лист на LBP-810 с экономией: родная раскладка (узкая строка по центру листа, блок a0d0 как у A4)."""
    return saver_810_active() and _PAGEPARMS_GEOM is not None


def is_810_mode():
    """LBP-810 включён (очередь с аргументом порта --model 810 или CAPT_ENABLE_810=1)."""
    return os.environ.get("CAPT_ENABLE_810") == "1"


def saver_810_active():
    """Экономия тонера на LBP-810 (13.10.2026). Родной драйвер шлёт её байтом a0d0[19] и печатает полутона
    крупными кластерами точек; принтер при экономии портит мелкие одиночные точки наших режимов smart/floyd
    в шум (сканы 13.10), а полный родной блок A4 810 нужен, чтобы экономия вообще включилась."""
    return is_810_mode() and SETTINGS["toner_saver"] == 1 and RESOLUTION_DPI == 600


def apply_paper_geometry(width_mm, height_mm, custom=False):
    """Подстраивает LINE_SIZE/LINES_BY_PAGE и геометрию a0d0 под реальный размер страницы
    задания (обычно вызывается из capt_print_pdf по page.rect PDF-страницы), но ТОЛЬКО если
    размер совпадает с известным откалиброванным размером бумаги (см. _KNOWN_PAPER_SIZES_MM)
    либо задание явно запросило свой размер (custom=True, из PostScript `*CustomPageSize`) и
    он укладывается в CUSTOM_SIZE_MIN_MM..CUSTOM_SIZE_MAX_MM. Любой другой размер (в т.ч. просто
    "необычная" PDF-страница) печатается как раньше - вписанным в A4, а не как отдельная бумага."""
    global LINE_SIZE, LINES_BY_PAGE, _PAGEPARMS_GEOM, A4_TRUE_SIZE
    A4_TRUE_SIZE = False
    a4 = abs(width_mm - 210.0) < 3 and abs(height_mm - 297.0) < 3
    # 05.10.2026 (скан a4_wide_test: рамка 2 мм целая со всех сторон): A4 как A5/A6 - канва на всю ширину листа.
    # CAPT_A4_WIDE=0 возвращает прежнее поведение (канва 4736 px по центру, поля ~4,7 мм слева и справа)
    a4_wide = a4 and os.environ.get("CAPT_A4_WIDE", "1") != "0" and not saver_810_active()  # 810+экономия: родная канва A4
    if a4 and not a4_wide:
        _PAGEPARMS_GEOM = None
        A4_TRUE_SIZE = True   # байты a0d0 для A4 прежние (канва 4736 px по центру листа 4960 px), страница рисуется 1:1
        apply_resolution(RESOLUTION_DPI)
        return
    matched = (210.0, 297.0) if a4_wide else None
    for w, h in _KNOWN_PAPER_SIZES_MM.values():
        if abs(width_mm - w) < 3 and abs(height_mm - h) < 3:
            matched = (w, h)
            break
    if matched is None and custom:
        if (CUSTOM_SIZE_MIN_MM[0] <= width_mm <= CUSTOM_SIZE_MAX_MM[0]
                and CUSTOM_SIZE_MIN_MM[1] <= height_mm <= CUSTOM_SIZE_MAX_MM[1]):
            matched = (width_mm, height_mm)
    if matched is None:
        _PAGEPARMS_GEOM = None  # неизвестный размер - печатаем как A4 (старое поведение)
        apply_resolution(RESOLUTION_DPI)
        return
    if RESOLUTION_DPI != 600:
        # геометрия не-A4 листов откалибрована только для 600 dpi - при 300 dpi печатаем как A4
        _PAGEPARMS_GEOM = None
        apply_resolution(RESOLUTION_DPI)
        return
    width_mm, height_mm = matched
    dpi = RESOLUTION_DPI
    mm_to_px = dpi / 25.4
    paper_w_px = (round(width_mm * mm_to_px) // 8) * 8  # кратно 8 для LINE_SIZE
    paper_h_px = round(height_mm * mm_to_px)
    LINE_SIZE = paper_w_px // 8
    # 30.09.2026 (линейка на листе A6 105x148, скан + эксперимент с height_buf):
    #  - принтер печатает первую строку растра на TOP_OFFSET_PX (=120 px, ~5мм) НИЖЕ переднего края
    #    листа (это поле [24:26] блока a0d0, "120" в обоих родных дампах) - верхние 5мм листа
    #    недоступны, поэтому растр = страница БЕЗ верхних 5мм (см. capt_print_pdf._render_gray_canvas);
    #  - поле "высота буфера" (height_buf) - жёсткий предел: строки растра за ним принтер ОТБРАСЫВАЕТ
    #    (раньше считалось "лист минус 237 px" по A4/B5 - и низ листа A5/A6 обрывался около 200 / 138мм).
    #    Ставим height_buf = числу отправляемых строк: печатается всё, что физически помещается на лист.
    LINES_BY_PAGE = paper_h_px - TOP_OFFSET_PX
    if saver_810_active():
        # LBP-810 + экономия, формат вручную (13.10.2026): раскладка по двум родным образцам (A4, B5 из дампов):
        # строка уже листа на 2 поля NATIVE810_MARGIN_PX (A4: 4736 px при листе 4960), высота буфера = лист - 237 px.
        LINE_SIZE = (paper_w_px - 2 * NATIVE810_MARGIN_PX) // 8
        LINES_BY_PAGE = paper_h_px - NATIVE810_HB_CUT
    _PAGEPARMS_GEOM = (LINE_SIZE, LINES_BY_PAGE, paper_w_px, paper_h_px)


def build_pageparms(settings=None):
    """38-байтный блок параметров страницы (a0d0 без 4-байтового заголовка команды, 34 байта)."""
    s = settings or SETTINGS
    dpi300 = s["resolution"] == 300
    if _PAGEPARMS_GEOM is not None and not dpi300:
        line_size, height_buf_px, paper_w_px, paper_h_px = _PAGEPARMS_GEOM
        p = bytearray([
            0x00, 0x00, 0xdd, 0x00, 0x07, 0x01, 0x00, 0x00, 0x1f, 0x1f,
            0x1f, 0x1f, 0x00, 0x11, 0x03, 0x01, 0x01, 0x01, 0x02, 0x00,
            0x00, 0x00,
        ])
        margin = 0
        if native810_geom():
            # родное начало блока 810 (A4: 05 00 a4 01 02 01), p22 = левое поле = (лист - строка) / 2
            p[0], p[2], p[3], p[4], p[5] = 0x05, 0xa4, 0x01, 0x02, 0x01
            margin = (paper_w_px - line_size * 8) // 2
        for val in (margin, 120, line_size, height_buf_px, paper_w_px, paper_h_px):
            p += bytes([val & 0xFF, (val >> 8) & 0xFF])
    else:
        p = bytearray([
            0x00, 0x00, 0xa4, 0x01, 0x02, 0x01, 0x00, 0x00, 0x1f, 0x1f,
            0x1f, 0x1f, 0x00, 0x11, 0x03, 0x01, 0x01, 0x01, 0x02, 0x00,
            0x00, 0x00, 0x70, 0x00, 0x78, 0x00, 0x50, 0x02, 0x7a, 0x1a,
            0x60, 0x13, 0x67, 0x1b,
        ])
    if A4_TRUE_SIZE and _PAGEPARMS_GEOM is None and not dpi300:
        # A4 1:1 (01.10.2026): height_buf в родных байтах 6778 строк отбрасывает нижние ~5 мм страницы
        # (линии у нижнего края пропадали на 1-3 px). Ставим все строки листа ниже отступа 120 px: 7016-120.
        hb = round(297 / 25.4 * 600) - 120
        p[28], p[29] = hb & 0xFF, (hb >> 8) & 0xFF
    if saver_810_active() and _PAGEPARMS_GEOM is None and not dpi300 and s["toner_saver"] == 1:
        # родной блок A4 LBP-810 побайтно (дамп 810_05/06): p0=05, высота буфера 6778 - иначе экономия не включается
        p[0] = 0x05
        p[28], p[29] = 0x7a, 0x1a
    p[8] = s["toner_density"]                      # Light=0x00, по умолчанию 0x1f, Dark=0x3f
    if s["refinement"] == 0:
        p[17], p[18] = 0x00, 0x00                   # Automatic Image Refinement выкл
    p[19] = s["toner_saver"]                        # Toner Saver
    if dpi300 and _PAGEPARMS_GEOM is None:
        p[13] = 0x00
        p[22:34] = bytes([0x38, 0x00, 0x3c, 0x00, 0x28, 0x01, 0x3e, 0x0d, 0xb0, 0x09, 0xb3, 0x0d])
    return bytes(p)


apply_resolution(SETTINGS["resolution"])

WAIT = 0.008  # 8000 usec, как в оригинале


_LANG_CACHE = None  # C4: файл не меняется в течение жизни процесса - читаем один раз


def _lang() -> str:
    """Язык, выбранный при установке (setup.ps1 пишет lang.txt рядом с программой)."""
    global _LANG_CACHE
    if _LANG_CACHE is not None:
        return _LANG_CACHE
    # lang.txt лежит рядом с exe (frozen) или со скриптом; прежнее место C:\CaptPrinter - запасное (v44 и старше)
    base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
    v = None
    for p in (os.path.join(base, "lang.txt"), r"C:\CaptPrinter\lang.txt"):
        try:
            with open(p, encoding="ascii") as f:
                v = f.read().strip().lower()
            break
        except OSError:
            continue
    _LANG_CACHE = v if v in ("ru", "en") else "ru"
    return _LANG_CACHE


def tr(ru: str, en: str) -> str:
    """Возвращает ru или en в зависимости от языка установки."""
    return ru if _lang() == "ru" else en


def _in_session0() -> bool:
    """Процесс запущен службой печати в сеансе 0 (без доступа к рабочему столу пользователя)."""
    try:
        import ctypes
        from ctypes import wintypes
        sess = wintypes.DWORD()
        ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(sess))
        return sess.value == 0
    except Exception:
        return False


def wts_message(title: str, msg: str, style: int = 0x40, timeout: int = 30, wait: bool = False):
    """Окно сообщения в сеансе вошедшего пользователя из процесса службы (14.10.2026). Redmon запускает нашу программу
    от имени системы в сеансе 0: всплывающие уведомления и MessageBox оттуда не видны (PermissionError 0x80070005).
    WTSSendMessage показывает окно на экране пользователя. Возвращает код ответа (1 ОК, 2 Отмена, 32000 истекло время,
    32001 без ожидания) или None, если показать не удалось."""
    import ctypes
    from ctypes import wintypes
    k32, wts = ctypes.windll.kernel32, ctypes.windll.wtsapi32
    sid = k32.WTSGetActiveConsoleSessionId()
    if sid in (0xFFFFFFFF, 0):
        return None
    resp = wintypes.DWORD(0)
    wts.WTSSendMessageW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD, wintypes.LPWSTR,
                                    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                    wintypes.BOOL]
    ok = wts.WTSSendMessageW(None, sid, title, len(title) * 2, msg, len(msg) * 2, style, timeout, ctypes.byref(resp),
                             bool(wait))
    return resp.value if ok else None


def user_dialog_ok_cancel(title: str, msg: str, timeout: int = 900):
    """Окно ОК/Отмена на экране пользователя. True - ОК, False - Отмена или время вышло, None - показать не удалось."""
    try:
        if _in_session0():
            r = wts_message(title, msg, 0x1 | 0x40 | 0x40000, timeout, True)   # ОК/Отмена, значок, поверх всех
            return None if r is None else (r == 1)
        import ctypes
        r = ctypes.windll.user32.MessageBoxW(0, msg, title, 0x1 | 0x40 | 0x1000 | 0x10000 | 0x40000)
        return None if r == 0 else (r == 1)
    except Exception:
        return None


def notify(title: str, msg: str, buttons=None) -> None:
    """
    Всплывающее уведомление Windows. Best-effort: печать не должна ломаться,
    если winotify/windows-toasts не установлен или показ не удался по любой причине.
    Используем AUMID командной строки ({1AC14E77-...}\\cmd.exe, зарегистрирован
    в Windows по умолчанию) - без этого трюка баннер тихо уходит в Центр
    уведомлений и пользователь его не видит (проверено 22.09.2026).
    """
    if title == "Canon LBP-1120" and is_810_mode():
        title = "Canon LBP-810"   # очередь 810: в уведомлениях своё название
    if _in_session0():
        # из Redmon тост показать нельзя - обычное окно в сеансе пользователя (само закроется через 30 с); кнопок у него нет
        try:
            hint = ""
            if buttons and any(u for _l, u in buttons):
                hint = tr("\n\nОбнулить счётчик картриджа: Counter.cmd (для 810 - Counter_810.cmd).",
                          "\n\nTo reset the cartridge counter run Counter.cmd (Counter_810.cmd for the 810).")
            if wts_message(title, msg + hint, 0x40 | 0x40000, 30, False) is not None:
                return
        except Exception:
            pass
    try:
        from windows_toasts import (InteractableWindowsToaster, Toast, ToastButton,
                                    ToastSystemButton, ToastSystemButtonAction)
        toast = Toast([title, msg])
        for label, url in (buttons or ()):
            # url: адрес с протокольной активацией (captcounter://...) либо None - кнопка просто закрывает тост
            toast.AddAction(ToastButton(label, "captcounter", launch=url) if url
                            else ToastSystemButton(ToastSystemButtonAction.Dismiss, label))
        InteractableWindowsToaster(title).show_toast(toast)
    except Exception as e:
        # 14.10.2026: сбой показа уведомления раньше терялся молча (при проверке с крышкой уведомления не было видно).
        # Пишем причину в общий журнал, печать это не ломает.
        try:
            import time as _t
            with open(os.path.join(SETTINGS_DIR, "capt_redmon.log"), "a", encoding="utf-8") as _f:
                _f.write(f"{_t.strftime('%Y-%m-%d %H:%M:%S')} [PID {os.getpid()}] уведомление не показано ({title!r}): {e!r}" + chr(10))
        except Exception:
            pass

# Сколько секунд ждать освобождения буфера принтера, прежде чем считать, что он завис.
# При нормальной печати тяжёлой страницы буфер освобождается за секунды.
BUFFER_WAIT_TIMEOUT = 60

LOCK_PATH = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "CaptPrinter", "device.lock")
LOCK_WAIT_TIMEOUT = 180  # секунд ждать освобождения принтера другим заданием


class DeviceLock:
    """
    Межпроцессный лок на устройство принтера. Redmon запускает ОТДЕЛЬНЫЙ
    процесс python на каждое задание печати - и с двух принтеров ("Canon
    LBP-1120" / "Canon LBP-1120 (sharp text)") это два независимых процесса,
    которые могут стартовать почти одновременно из разных приложений. Без
    лока оба процесса могут одновременно открыть один и тот же USB-девайс и
    вызвать set_configuration() друг у друга посреди задания - именно так
    воспроизводилась потеря первого листа при двух подряд запусках
    (см. AUDIT_2026-09-22.md, находки S1/S3). Лок сериализует ЦЕЛИКОМ работу
    с устройством: второе задание просто ждёт своей очереди, как было бы
    с одним физическим принтером и без параллелизма.
    Реализовано на msvcrt.locking() (стандартная библиотека, без pywin32) -
    файловый advisory-лок, который сам снимается, если процесс-владелец
    аварийно завершился (ОС закрывает файловый дескриптор).
    """

    def __init__(self, path: str = LOCK_PATH, timeout: float = LOCK_WAIT_TIMEOUT):
        self.path = path
        self.timeout = timeout
        self.f = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.f = open(self.path, "a+b")
        deadline = time.time() + self.timeout
        while True:
            try:
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                return self
            except OSError:
                if time.time() > deadline:
                    self.f.close()
                    raise TimeoutError(
                        f"Принтер занят другим заданием печати дольше {self.timeout} с - "
                        "проверьте очередь печати (два принтера 'Canon LBP-1120' используют одно устройство).")
                time.sleep(0.2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.f.seek(0)
            msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        self.f.close()
        return False


class Compressor:
    """Порт compress_bitmap()/out_packet()/out_packet_buf() из capt.c."""

    def __init__(self, packet_limit: int = 65500):
        self.packet_limit = packet_limit
        self.packets = []          # список bytes-объектов, каждый - отдельный USB-пакет (<=65536)
        self.band = bytearray()    # текущий "band" (побайтовый буфер)
        self.cur = bytearray()     # текущий собираемый пакет (начинается с a0 c0 00 00)
        self.csize = 4
        self._new_packet()

    def _new_packet(self):
        self.cur = bytearray([0xa0, 0xc0, 0x00, 0x00])
        self.csize = 4

    def out_packet_buf(self, data: bytes):
        self.band.extend(data)
        if len(self.band) > 65535:
            raise RuntimeError("band too big")

    def out_packet(self, *cbytes):
        """cbytes - до 4 байт для добавления в band, либо специальные маркеры через out_packet_ctrl."""
        self.band.extend(cbytes)
        if len(self.band) > 65535:
            raise RuntimeError("band too big")

    def flush_band(self, is_last_band: bool):
        if self.csize + len(self.band) > self.packet_limit:
            self._flush_packet(last=False)
        self.csize += len(self.band)
        self.cur.extend(self.band)
        self.band = bytearray()

    def _flush_packet(self, last: bool):
        if last:
            self.cur.append(0x42)
            self.csize += 1
        self.cur[2] = self.csize & 0xFF
        self.cur[3] = (self.csize >> 8) & 0xFF
        self.packets.append(bytes(self.cur))
        if not last:
            self._new_packet()

    def finish(self):
        self._flush_packet(last=True)
        return self.packets


def encode_line_diff(comp: Compressor, cline: bytes, diff: int):
    """
    Полный порт основного тела for-цикла из compress_bitmap() (capt.c, строки 342-447).
    cline должен быть дополнен минимум 4 байтами "хвоста" за пределами diff,
    чтобы безопасно читать cline[lpos+1..lpos+3] у конца строки (как это делает C
    с запасом в буфере).
    """
    state = 0  # 0 - нет повтора, -1 - в повторе
    rep = 0
    lpos = 0
    while lpos < diff:
        if (cline[lpos] == cline[lpos + 1]) and ((lpos + 1) < diff):
            if state == -1:
                if rep == 255:
                    c1 = 0xa0 | (rep >> 3)
                    c2 = 0x80 | ((rep & 0x07) << 3)
                    comp.out_packet_buf(bytes([c1, c2, cline[lpos]]))
                    rep = 0
                    state = 0
                else:
                    rep += 1
            else:
                state = -1
                rep = 2
        else:
            if state == 0:
                rep = 1
                c_start = lpos
                while rep < 255:
                    if lpos + rep + 2 >= diff:
                        rep += diff - (lpos + rep)
                        break
                    elif (cline[lpos + rep] != cline[lpos + rep + 1]) or (cline[lpos + rep + 1] != cline[lpos + rep + 2]):
                        rep += 1
                    else:
                        break
                if rep > 255:
                    rep = 255
                lpos_new = lpos + rep - 1
                if rep < 8:
                    c1 = rep << 3
                    comp.out_packet_buf(bytes([c1]))
                else:
                    c1 = 0xa0 | (rep >> 3)
                    c2 = 0xc0 | ((rep & 0x07) << 3)
                    comp.out_packet_buf(bytes([c1, c2]))
                comp.out_packet_buf(bytes(cline[c_start:c_start + rep]))
                rep = 0
                lpos = lpos_new
            else:
                if rep < 8:
                    if (((cline[lpos + 1] != cline[lpos + 2]) or ((lpos + 2) >= diff)) and ((lpos + 1) < diff)):
                        c1 = 0xc1 | (rep << 3)
                        comp.out_packet_buf(bytes([c1, cline[lpos], cline[lpos + 1]]))
                        lpos += 1
                    else:
                        c1 = 0x40 | (rep << 3)
                        comp.out_packet_buf(bytes([c1, cline[lpos]]))
                else:
                    if (((cline[lpos + 1] != cline[lpos + 2]) or ((lpos + 2) >= diff)) and ((lpos + 1) < diff)):
                        if (((cline[lpos + 2] != cline[lpos + 3]) or ((lpos + 3) >= diff)) and ((lpos + 2) < diff)):
                            c1 = 0xa0 | (rep >> 3)
                            c2 = 0x02 | ((rep & 0x07) << 3)
                            comp.out_packet_buf(bytes([c1, c2, cline[lpos]]))
                            comp.out_packet_buf(bytes([cline[lpos + 1], cline[lpos + 2]]))
                            lpos += 2
                        else:
                            c1 = 0xa0 | (rep >> 3)
                            c2 = 0x01 | ((rep & 0x07) << 3)
                            comp.out_packet_buf(bytes([c1, c2, cline[lpos], cline[lpos + 1]]))
                            lpos += 1
                    else:
                        c1 = 0xa0 | (rep >> 3)
                        c2 = 0x80 | ((rep & 0x07) << 3)
                        comp.out_packet_buf(bytes([c1, c2, cline[lpos]]))
                state = 0
        lpos += 1


def last_difference(cur: bytes, prev: bytes) -> int:
    diff = -1
    for i in range(LINE_SIZE):
        if cur[i] != prev[i]:
            diff = i
    return diff


def compress_page_v1(line_source):
    """
    line_source: функция() -> bytes длиной LINE_SIZE, возвращающая очередную строку растра.
    Полный порт compress_bitmap() для произвольного (не обязательно однородного) содержимого.
    """
    comp = Compressor(packet_limit=PACKET_LIMIT)
    pad = bytes(4)  # запас для безопасного чтения cline[lpos+1..lpos+3] у края строки

    prev_line = None
    cur_line = line_source() + pad
    diff = LINE_SIZE
    linecnt = 0

    while linecnt < LINES_BY_PAGE:
        comp.out_packet(0x40)
        cnt = min(ROWS_BY_BAND, LINES_BY_PAGE - linecnt)

        while True:
            encode_line_diff(comp, cur_line, diff)
            if diff < LINE_SIZE:
                comp.out_packet(0x41)
            comp.flush_band(is_last_band=False)  # граница пакета возможна после каждой строки (куски <= PACKET_LIMIT, как у родного драйвера)

            prev_line = cur_line
            linecnt += 1
            cur_line = line_source() + pad if linecnt < LINES_BY_PAGE else bytes(LINE_SIZE) + pad

            if cnt > 0:
                diff = last_difference(cur_line, prev_line) + 1
                cnt -= 1
            else:
                diff = LINE_SIZE
                break

        comp.out_packet(0x40)
        comp.flush_band(is_last_band=False)

    return comp.finish()

# ---------------------------------------------------------------------------
# Кодировщик v2 (24.09.2026). Формат расшифрован по USB-дампам родного драйвера
# Canon (тесты: линия/квадрат/сетка; usb_dumps-05): помимо литералов и
# повторов из capt.c есть операция "пропустить N*8 байт из предыдущей строки".
# Первая строка полосы кодируется целиком, остальные - как разница с
# предыдущей: пропуски неизменных участков + изменённые отрезки + 0x41.
#   0x40 / 0x40         начало и конец полосы, 0x41 - конец строки
#   0x80|n              пропустить n*8 байт (n=0..31)
#   (cnt<<3)|sb         литерал cnt(1..7) байт, перед ним пропуск sb(0..7)
#   0xA0|hi, 0xC0|((cnt&7)<<3)|sb, данные   литерал cnt=(hi<<3)|(cnt&7) до 255
#   0x40|(rep<<3), v    повтор v rep(1..7) раз
#   0xA0|hi, 0x80|((rep&7)<<3), v           повтор v до 255 раз
# Перед отправкой результат проверяется обратным декодированием; при любом
# расхождении/ошибке используется прежний кодировщик (compress_page_v1).
# ---------------------------------------------------------------------------
_MIN_RUN = 4
_GAP_MERGE = 3


def _v2_lit_op(data: bytes, sb: int) -> bytes:
    n = len(data)
    if n < 8:
        return bytes([(n << 3) | sb]) + data
    return bytes([0xA0 | (n >> 3), 0xC0 | ((n & 7) << 3) | sb]) + data


def _v2_run_op(v: int, n: int) -> bytes:
    if n < 8:
        return bytes([0x40 | (n << 3), v])
    return bytes([0xA0 | (n >> 3), 0x80 | ((n & 7) << 3), v])


def _v2_encode_span(span: bytes, sb: int, first_is_literal: bool) -> bytes:
    """Кодирует непрерывный отрезок. sb (0..7) - пропуск перед ним, цепляется к первому
    литералу (короткому: вариант ext-литерала с sb != 0 дампами не проверен)."""
    out = bytearray()
    lit = bytearray()
    first = True
    i = 0
    n = len(span)

    def flush_lit():
        nonlocal first
        while lit:
            lim = 7 if (first and sb) else 255
            chunk = bytes(lit[:lim])
            del lit[:lim]
            out.extend(_v2_lit_op(chunk, sb if first else 0))
            first = False

    while i < n:
        j = i
        while j < n and span[j] == span[i]:
            j += 1
        r = j - i
        if r >= _MIN_RUN and not (first_is_literal and first and not lit):
            flush_lit()
            while r > 0:
                k = min(r, 255)
                out.extend(_v2_run_op(span[i], k))
                i += k
                r -= k
        else:
            lit.extend(span[i:j])
            i = j
    flush_lit()
    return bytes(out)


def _v2_encode_line(cur: bytes, prev) -> bytes:
    """prev None => первая строка полосы, кодируется целиком."""
    if prev is None:
        return _v2_encode_span(cur, 0, False)
    changed = [i for i in range(LINE_SIZE) if cur[i] != prev[i]]
    if not changed:
        return b"A"
    spans = []
    s = e = changed[0]
    for c in changed[1:]:
        if c - e - 1 < _GAP_MERGE:
            e = c
        else:
            spans.append((s, e + 1))
            s = c
        e = c
    spans.append((s, e + 1))
    out = bytearray()
    pos = 0
    for a, b in spans:
        gap = a - pos
        units = gap // 8
        while units > 0:
            k = min(units, 31)
            out.append(0x80 | k)
            units -= k
        out.extend(_v2_encode_span(cur[a:b], gap % 8, True))
        pos = b
    if pos < LINE_SIZE:
        out.append(0x41)
    return bytes(out)


def _v2_decode(packets):
    """Обратное декодирование для самопроверки: пакеты (a0 c0 len len + данные) -> список строк."""
    s = b"".join(p[4:] for p in packets)
    i = 0
    prev = bytearray(LINE_SIZE)
    cur = bytearray(prev)
    pos = 0
    lines = []
    while i < len(s):
        b = s[i]
        i += 1
        if b == 0x40:
            prev = bytearray(LINE_SIZE)
            cur = bytearray(prev)
            pos = 0
            continue
        if b == 0x42:
            break
        if b == 0x41:
            lines.append(bytes(cur))
            prev = cur
            cur = bytearray(prev)
            pos = 0
            continue
        if b & 0xE0 == 0xA0:
            c2 = s[i]
            i += 1
            rep = ((b & 0x1F) << 3) | ((c2 >> 3) & 7)
            k = c2 & 0xC0
            if k == 0xC0:
                d = s[i:i + rep]
                i += rep
                pos += c2 & 7
            elif k == 0x80:
                d = bytes([s[i]]) * rep
                i += 1
            else:
                raise ValueError("неизвестная операция")
        elif b & 0xC0 == 0x80:
            pos += (b & 0x1F) * 8
            d = b""
        elif b & 0xC0 == 0:
            rep = (b >> 3) & 7
            d = s[i:i + rep]
            i += rep
            pos += b & 7
        elif b & 0xC0 == 0x40:
            rep = (b >> 3) & 7
            d = bytes([s[i]]) * rep
            i += 1
        else:
            raise ValueError("неизвестная операция")
        cur[pos:pos + len(d)] = d
        pos += len(d)
        if pos >= LINE_SIZE:
            lines.append(bytes(cur))
            prev = cur
            cur = bytearray(prev)
            pos = 0
    return lines


def compress_page_v2(lines):
    """lines: LINES_BY_PAGE строк по LINE_SIZE байт. Возвращает список пакетов a0 c0
    размером не более PACKET_LIMIT (граница пакета - на границе строки, как у родного драйвера)."""
    comp = Compressor(packet_limit=PACKET_LIMIT)
    ln = 0
    total = len(lines)
    while ln < total:
        comp.out_packet_buf(b"@")
        comp.flush_band(is_last_band=False)
        cnt = min(ROWS_BY_BAND, total - ln)
        prev = None
        for _ in range(cnt):
            cur = lines[ln]
            comp.out_packet_buf(_v2_encode_line(cur, prev))
            comp.flush_band(is_last_band=False)
            prev = cur
            ln += 1
        comp.out_packet_buf(b"@")
        comp.flush_band(is_last_band=False)
    return comp.finish()


# 05.10.2026: упаковка v2 отключена. На сканах (05.10, тест-лист в smart2) принтер выдавал сдвиг
# левой рамки таблицы на 1 байт (8 px) на полосах 27-31; тот же растр, упакованный v1, печатается
# без сдвига (разброс 0,19 px); растр до отправки идеально прямой. Правила пропуска v2 выведены
# из ограниченных дампов, самопроверка `_v2_decode` не проверяет поведение принтера. Код v2 оставлен
# для разбора (USE_V2 = True включает его обратно).
USE_V2 = False


def compress_page(line_source, logger=None):
    """
    line_source: функция() -> bytes длиной LINE_SIZE, возвращающая очередную строку растра.
    По умолчанию упаковка только прежним кодировщиком v1 (порт capt.c). При USE_V2 кодирует
    обоими и берёт меньший результат (v2 проверяется обратным декодированием).
    """
    lines = [line_source() for _ in range(LINES_BY_PAGE)]
    it = iter(lines)
    p1 = compress_page_v1(lambda: next(it))
    if not USE_V2:
        return p1
    try:
        p2 = compress_page_v2(lines)
        if sum(map(len, p2)) < sum(map(len, p1)):
            if _v2_decode(p2) == lines:
                return p2
            if logger:
                logger("  кодировщик v2: проверка не прошла, использую прежний")
    except Exception as e:
        if logger:
            logger(f"  кодировщик v2: {e!r}, использую прежний")
    return p1



def make_stripe_pattern_source(stripe_height=200):
    """Чередующиеся чёрные/белые горизонтальные полосы для проверки реального кодирования."""
    state = {"i": 0}

    def get_line():
        i = state["i"]
        state["i"] += 1
        black = (i // stripe_height) % 2 == 1
        return bytes([0xFF if black else 0x00]) * LINE_SIZE

    return get_line


def compress_blank_page():
    """
    Специальный случай общего алгоритма из capt.c: страница целиком из
    одинаковых байт value (полностью белая). Все строки после первой
    идентичны предыдущей => diff=0 для них => почти не дают вывода.
    Реализовано так же, как compress_bitmap(), но без чтения PBM-файла -
    просто эмулируем "линию" как constant-массив нужного значения.
    """
    comp = Compressor()
    value = 0x00  # белый пиксель (0 = белый, соответствует общепринятому для этого формата)

    diff = LINE_SIZE  # первая строка должна быть закодирована полностью
    linecnt = 0

    band_idx = 0
    while linecnt < LINES_BY_PAGE:
        comp.out_packet(0x40)  # начало band
        cnt = min(ROWS_BY_BAND, LINES_BY_PAGE - linecnt)

        while True:
            if diff > 0:
                # Кодируем одну "строку" длиной diff одинаковых байт как повтор (RLE state=-1 путь)
                _encode_repeat_run(comp, value, diff)

            # ВАЖНО: маркер "строка не изменилась" шлётся НА КАЖДУЮ строку с diff<LINE_SIZE,
            # а не один раз на весь band - это и была причина бага с полосами на печати.
            if diff < LINE_SIZE:
                comp.out_packet(0x41)

            # Переход к следующей строке
            linecnt += 1
            if cnt > 0:
                diff = 0  # все следующие строки совпадают с предыдущей (страница однородная)
                cnt -= 1
            else:
                diff = LINE_SIZE
                break

        comp.out_packet(0x40)
        comp.flush_band(is_last_band=False)
        band_idx += 1

    return comp.finish()


def _encode_repeat_run(comp: Compressor, value: int, length: int):
    """
    Кодирует последовательность из `length` одинаковых байт `value`
    по правилам из capt.c (ветка repeated bytes, "11 syntax").
    Разбиваем на куски по 255 (максимум для одного repeat-кода).
    """
    remaining = length
    while remaining > 0:
        rep = min(remaining, 255)
        if rep < 8:
            c1 = 0x20 | (rep << 3)
            comp.out_packet_buf(bytes([c1, value]))
        else:
            c1 = 0xa0 | (rep >> 3)
            c2 = 0x80 | ((rep & 0x07) << 3)
            comp.out_packet_buf(bytes([c1, c2, value]))
        remaining -= rep


class Status:
    def __init__(self, raw: bytes):
        self.raw = raw

    @property
    def buffer_full(self):
        if len(self.raw) < 5:
            return True
        return bool(self.raw[4] & 0x08) or self.raw[0] == 0x00


def parse_error_flags(a0a0_result):
    """
    Разбирает payload ответа на команду a0a0 (16 байт после 6-байтного заголовка)
    на флаги ошибок. Расшифровано вживую 28.09.2026 опросом реального принтера
    (status_probe.py) при поочерёдных: открытой крышке, физическом замятии листа
    в валиках во время печати, извлечённом картридже и наличии/отсутствии бумаги
    в лотке - см. project_canon_lbp1120_* в памяти. Биты независимы друг от друга:
      payload[1] & 0x40 - картридж не установлен (или не до конца вставлен):
                           ЗАЩЁЛКИВАЕТСЯ, снимается только выключением/включением
      payload[2] & 0x80 - бумага физически лежит в лотке (весовой датчик)
      payload[4] & 0x40 - замятие: ЗАЩЁЛКИВАЕТСЯ и не снимается ни чтением статуса,
                           ни переоткрытием крышки, ни командами a1a1/a0a2/a4e0/a5e0/a9e0 -
                           проверено; снимается только выключением/включением принтера
      payload[5] & 0x40 - крышка открыта (живой бит, пропадает сразу при закрытии)
    Возвращает None, если ответ короче ожидаемого (нет данных для диагностики).
    """
    payload = a0a0_result[1] if a0a0_result and len(a0a0_result) > 1 and a0a0_result[1] else None
    if not payload or len(payload) < 6:
        return None
    return {
        "paper_present": bool(payload[2] & 0x80),
        "no_cartridge": bool(payload[1] & 0x40),
        "jam": bool(payload[4] & 0x40),
        "cover_open": bool(payload[5] & 0x40),
    }


def error_flags_message(flags):
    """Текст для пользователя по самому приоритетному найденному флагу
    (нет картриджа важнее замятия важнее крышки)."""
    if not flags:
        return None
    if flags["no_cartridge"] and not flags.get("paper_present", True) and not flags["jam"] and not flags["cover_open"]:
        # 14.10.2026 (нагрузка 25 стр., бумага кончилась на 17-й): при пустом лотке принтер ставит тот же бит, что и при
        # проблеме с подачей, и старый текст говорил про картридж. Лоток пуст - так и пишем; после загрузки бумаги
        # драйвер сам переподключается и допечатывает страницу.
        return tr(
            "В лотке закончилась бумага. Положите бумагу, печать продолжится сама.",
            "The paper tray is empty. Load paper and printing will continue by itself.")
    if flags["no_cartridge"]:
        # 07.10.2026: текст раньше уверенно обвинял картридж. Два живых случая подряд этот же
        # бит (payload[1]&0x40) сработал не от картриджа: один раз просто ещё не было бумаги
        # (это теперь не проверяется в wait_for_paper), второй раз - пользователь приподнял лист
        # в момент захвата принтером. Бит ЗАЩЁЛКИВАЕТСЯ (не снимается до выключения/включения),
        # поэтому надёжно отличить "действительно нет картриджа" от "задели бумагу при подаче"
        # программно пока нельзя - нужен контролируемый повтор status_probe.py. Сообщение честно
        # перечисляет обе вероятные причины вместо того, чтобы безосновательно указывать на картридж.
        return tr(
            "Принтер сообщил о проблеме с картриджем или подачей бумаги (возможно, лист задели "
            "рукой во время захвата). Проверьте картридж и не трогайте бумагу во время печати, "
            "затем выключите/включите принтер - это обязательно, ошибка не снимается сама.",
            "The printer reported a cartridge or paper-feed problem (the sheet may have been "
            "touched while it was being pulled in). Check the cartridge and don't touch the paper "
            "while printing, then power-cycle the printer - required, this error doesn't clear itself.")
    if flags["jam"]:
        return tr(
            "Замятие бумаги в принтере. Извлеките застрявший лист и выключите/включите принтер.",
            "Paper jam in the printer. Remove the stuck sheet and power-cycle the printer.")
    if flags["cover_open"]:
        return tr("Открыта крышка принтера. Закройте крышку.", "The printer cover is open. Close it.")
    return None


def detect_model(prefer="auto"):
    """Какой принтер печатает по умолчанию вне очереди (картинки по правому клику, командная строка), 14.10.2026:
    "1120" / "810" / None. prefer: auto (1120, а если его нет - 810), 1120, 810."""
    try:
        backend = libusb_package.get_libusb1_backend()
        found = set()
        for d in usb.core.find(find_all=True, idVendor=VENDOR_ID, backend=backend):
            found.add(d.idProduct)
            usb.util.dispose_resources(d)
    except Exception:
        return None
    has1120, has810 = PRODUCT_ID in found, PRODUCT_ID_810 in found
    if prefer == "810":
        return "810" if has810 else ("1120" if has1120 else None)
    if prefer == "1120":
        return "1120" if has1120 else ("810" if has810 else None)
    return "1120" if has1120 else ("810" if has810 else None)


def find_printer(backend=None, logger=None):
    """Выбор принтера при нескольких подключённых (03.10.2026). Серийный номер берётся из
    переменной CAPT_PRINTER_SERIAL или settings.ini (printer_serial); пусто - первый найденный.
    Нужный номер задан, но такого принтера нет - None (печать не должна уйти на чужой).
    Дескрипторы лишних устройств закрываются: чтение serial_number держит устройство
    открытым, и повторное открытие даёт Access denied."""
    backend = backend or libusb_package.get_libusb1_backend()
    pids = {PRODUCT_ID}
    if os.environ.get("CAPT_ENABLE_810") == "1":
        pids.add(PRODUCT_ID_810)
    devs = list(usb.core.find(find_all=True, idVendor=VENDOR_ID,
                              custom_match=lambda d: d.idProduct in pids, backend=backend))
    want = (os.environ.get("CAPT_PRINTER_SERIAL") or SETTINGS.get("printer_serial") or "").strip().lower()
    if not want and os.environ.get("CAPT_ENABLE_810") == "1":
        # очередь 810 без серийного номера (аудит F5, 13.10.2026): берём только 810, а не первый из двух моделей
        only810 = [d for d in devs if d.idProduct == PRODUCT_ID_810]
        for d in devs:
            if d not in only810:
                usb.util.dispose_resources(d)
        devs = only810
    if not want:
        for extra in devs[1:]:
            usb.util.dispose_resources(extra)
        if len(devs) > 1 and logger:
            logger(f"  подключено принтеров: {len(devs)}, выбран первый найденный; "
                   "задайте printer_serial в settings.ini, чтобы выбрать нужный")
        return devs[0] if devs else None
    chosen = None
    for d in devs:
        try:
            ok = str(d.serial_number).strip().lower() == want
        except usb.core.USBError:
            ok = False
        if ok and chosen is None:
            chosen = d
            if logger:
                logger(f"  принтер выбран по серийному номеру: {d.serial_number}")
        else:
            usb.util.dispose_resources(d)
    return chosen


class Printer:
    def __init__(self, logger=print):
        """
        logger: куда идёт построчная диагностика (по умолчанию print - для
        прямого запуска из консоли). capt_print_redmon.py передаёт свою
        функцию log(), которая пишет в файл, а не в stdout - иначе под
        Redmon (Output=0, никто не читает stdout процесса) труба заполняется
        и process зависает на очередном print() (находка S12).
        """
        self.logger = logger
        backend = libusb_package.get_libusb1_backend()
        self.dev = find_printer(backend, logger)
        if self.dev is None:
            want = os.environ.get("CAPT_PRINTER_SERIAL") or SETTINGS.get("printer_serial")
            raise RuntimeError(f"Принтер с серийным номером {want} не найден" if want else "Принтер не найден")
        self.dev.set_configuration()
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        self.ep_out = usb.util.find_descriptor(
            intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.ep_in = usb.util.find_descriptor(
            intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
        try:
            self.dev.clear_halt(self.ep_out.bEndpointAddress)
            self.dev.clear_halt(self.ep_in.bEndpointAddress)
        except usb.core.USBError:
            pass
        self._flush_input()

    def _flush_input(self):
        try:
            while True:
                self.dev.read(self.ep_in.bEndpointAddress, 4096, timeout=200)
        except usb.core.USBError:
            pass

    def write_command(self, one, two, buf: bytes = b'', nread=0, uwait=0.0):
        packet = bytes([one, two, 0x04 + len(buf), 0x00]) + buf
        self.logger(f"  w: {packet.hex()}")
        self.dev.write(self.ep_out.bEndpointAddress, packet, timeout=10000)
        time.sleep(WAIT)
        results = []
        for _ in range(nread):
            try:
                data = bytes(self.dev.read(self.ep_in.bEndpointAddress, 256, timeout=10000))
            except usb.core.USBError as e:
                self.logger(f"  r: ERROR {e}")
                data = b''
            self.logger(f"  r: {data.hex()}")
            results.append(data)
            time.sleep(WAIT)
        if uwait > 0:
            time.sleep(uwait)
        return results

    def wait_for_paper(self):
        for i in range(120):
            r0 = self.write_command(0xa0, 0xa0, nread=2)
            r = self.write_command(0xa1, 0xa0, nread=2)
            flags = parse_error_flags(r0)
            # 07.10.2026: no_cartridge НЕ проверяем здесь. Живой случай: пользователь просто не
            # успел положить лист, а флаг "нет картриджа" уже горел - ожидание бумаги оборвалось
            # мгновенно с неверным сообщением про картридж, хотя картридж был на месте. Похоже,
            # тест 28.09, которым расшифровали payload[1]&0x40 как "нет картриджа", ставился с
            # одновременно пустым лотком - бит может означать более общее "не готов к печати",
            # включающее и отсутствие бумаги. Пока не переразобрано по отдельности - здесь ловим
            # только jam/cover_open (менее вероятно спутать с "просто ждём бумагу"); если бумага
            # и правда не появится 120 с - честный таймаут ниже, без ложного обвинения картриджа.
            if flags and (flags["jam"] or flags["cover_open"]):
                msg = error_flags_message(flags)
                notify("Canon LBP-1120", msg)
                raise RuntimeError(msg)
            if len(r) >= 2 and len(r[1]) > 10 and r[1][10] == 0xfd:
                return True
            if i == 0:
                self.logger("  Ожидание бумаги...")
                notify("Canon LBP-1120", tr(
                    "Нет бумаги в лотке. Принтер ждёт до 2 минут, положите лист.",
                    "No paper in the tray. The printer waits up to 2 minutes, please load a sheet."))
            time.sleep(1.0)
        return False

    def _log_buffers_field(self, r):
        """
        Диагностика (не влияет на печать): в проекте captdriver (LBP2900+, другое
        поколение протокола CAPT, issue #38) в ответе на 0xA1A1 на офсете 12-13
        лежит поле "Buffers" (кол-во буферов по 32 КБ; LBP1120 = 16 = 512 КБ по их
        таблице). Наш протокол (Boichat, LBP-810/1120) старше и может отличаться по
        структуре ответа - здесь только логируем сырые байты и кандидата на разбор,
        чтобы сверить с уже известным реальным пределом печати (~512 КБ по сервис-мануалу).
        """
        for i, resp in enumerate(r):
            self.logger(f"  status[{i}]: {resp.hex()} ({len(resp)} байт)")
        payload = r[1] if len(r) > 1 else b''
        if len(payload) >= 14:
            le = int.from_bytes(payload[12:14], "little")
            be = int.from_bytes(payload[12:14], "big")
            self.logger(f"  кандидат 'Buffers' (офсет 12-13): LE={le} ({le*32768} байт={le*32/1024:.1f} КБ), "
                        f"BE={be} ({be*32768} байт={be*32/1024:.1f} КБ)")
        else:
            self.logger(f"  ответ короче 14 байт ({len(payload)}), поле Buffers на офсете 12-13 недоступно")

    def wait_until_done(self, timeout=150):
        """
        Ждёт, пока принтер реально допечатает страницу. Родной драйвер после последнего
        куска данных ещё ~20 с опрашивает принтер (a0e0 + a1a0 каждые ~0.2 с; при бите
        события в ответе a0e0 - запрос a0a0 с 16-байтным состоянием датчиков бумаги; на
        последнем шаге состояние 0x02 - команда a9e0; конец - бит 0x40 в ответе a0a0)
        - по USB-дампам 24.09.2026. Наш драйвер выходил сразу после отправки данных:
        задание пропадало из очереди, пока принтер ещё принимал/печатал страницу, и
        следующее задание (сброс/инициализация принтера) давало пустой лист, обрыв или
        малую часть страницы. Пока эта функция работает, DeviceLock держится и
        следующее задание ждёт. По таймауту не падаем - только пишем в лог.
        """
        deadline = time.time() + timeout
        self._underrun_reported = False
        self.logger("  Жду, пока принтер допечатает страницу...")
        sent_end = False
        end_deadline = None
        while time.time() < deadline:
            if sent_end:
                # после a9e0 родной драйвер опрашивает только a0a0 (~раз в секунду):
                # бит 0x40 в её ответе - страница выдана. Ответ a0e0 в это время не
                # несёт события (у нас "0x8800" бесконечно - на этом застревало ожидание).
                r2 = self.write_command(0xa0, 0xa0, nread=2)
                hdr = r2[0] if r2 else b''
                self._check_underrun(r2)
                if len(hdr) >= 5 and (hdr[4] & 0x40):
                    self.logger("  Принтер закончил печать страницы.")
                    return True
                if time.time() > end_deadline:
                    self.logger("  После a9e0 признак конца не пришёл за 30 с - считаю страницу допечатанной.")
                    return True
                time.sleep(0.5)
                continue
            r = self.write_command(0xa0, 0xe0, nread=1)
            st = r[0] if r else b''
            if len(st) >= 6 and (st[5] & 0x01):
                r2 = self.write_command(0xa0, 0xa0, nread=2)
                hdr = r2[0] if r2 else b''
                payload = r2[1] if len(r2) > 1 else b''
                self._check_underrun(r2)
                if payload and (payload[0] & 0x0f) == 0x02:
                    self.write_command(0xa9, 0xe0, nread=1)
                    sent_end = True
                    end_deadline = time.time() + 30
                    continue
                if len(hdr) >= 5 and (hdr[4] & 0x40):
                    self.logger("  Принтер закончил печать страницы.")
                    return True
            self.write_command(0xa1, 0xa0, nread=2)
            time.sleep(0.15)
        self.logger(f"  Принтер не сообщил о завершении печати за {timeout} с - продолжаю без ожидания.")
        return False

    def _check_underrun(self, a0a0_result):
        """Флаг payload[1] & 0x02 в a0a0 после отправки страницы: принтер не получил данные
        вовремя, лист вышел обрезанным посередине. Лог 29-30.09.2026: был у всех обрезанных
        заданий (декларация, сертификат) и ни у одного целого. Сообщаем один раз на страницу."""
        payload = a0a0_result[1] if a0a0_result and len(a0a0_result) > 1 and a0a0_result[1] else b''
        if len(payload) >= 2 and (payload[1] & 0x02) and not getattr(self, "_underrun_reported", False):
            self._underrun_reported = True
            self.logger("  ВНИМАНИЕ: принтер сообщил, что страница напечатана НЕ полностью (флаг 0x02 в a0a0).")
            notify("Canon LBP-1120", tr(
                "Страница напечатана не полностью (обрыв посередине листа) - слишком сложная страница. "
                "Повторите печать.",
                "The page was printed only partially (cut in the middle) - the page is too complex. "
                "Print it again."))

    def ack_status_change(self, r):
        """Принтер выставляет в a0e0 биты "статус изменился" (байт 5, младшие 2 бита) и,
        пока хост не прочитает a0a0 (и a1a0), держит их и перестаёт принимать данные:
        буфер "полон" навсегда (живой лог 25.09.2026: 347 опросов подряд 1a0d, таймаут на
        пакете 53/76, страница обрывается). Родной драйвер читает a0a0/a1a0 сразу (дамп 31)."""
        st = r[0] if r else b''
        if len(st) >= 6 and (st[5] & 0x03):
            self.write_command(0xa0, 0xa0, nread=2)
            self.write_command(0xa1, 0xa0, nread=2)
            return True
        return False

    def print_page(self, page_bytes_packets, first_page=True, wait_done=True):
        if first_page:
            r = self.write_command(0xa1, 0xa1, nread=2)
            if not r or len(r[0]) < 2 or r[0][0] != 0xa1 or r[0][1] != 0xa1:
                raise RuntimeError("Принтер не отвечает корректно (не подключён?)")
            self._log_buffers_field(r)

        if not self.wait_for_paper():
            raise TimeoutError("Таймаут ожидания бумаги")

        if first_page:
            self.write_command(0xa0, 0xa2, nread=1)
            self.write_command(0xa0, 0xe0, nread=1)
            self.write_command(0xa1, 0xa0, nread=2)
            self.write_command(0xa4, 0xe0, nread=1)
            self.write_command(0xa5, 0xe0, buf=bytes([0xee, 0xdb, 0xea, 0xad, 0, 0, 0, 0]), nread=1)
            self.write_command(0xa0, 0xe0, nread=1)
            self.write_command(0xa0, 0xa0, nread=2)
            self.write_command(0xa1, 0xa0, nread=2)
            self.write_command(0xa0, 0xe0, nread=1)

        pageparms = build_pageparms()
        self.write_command(0xa0, 0xd0, buf=pageparms, nread=0)

        self.write_command(0xa0, 0xe0, nread=1)
        self.write_command(0xa1, 0xd0, nread=0)
        self.write_command(0xa0, 0xe0, nread=1)
        self.write_command(0xa0, 0xa0, nread=2)
        self.write_command(0xa1, 0xa0, nread=2)

        # K3: ОДИН дедлайн на весь набор пакетов страницы, а не свой заново на
        # каждый пакет. Раньше wait_started сбрасывался в начале каждой итерации
        # цикла - в худшем случае (принтер то освобождает буфер на секунду, то
        # снова встаёт) реальное ожидание могло набежать до N x BUFFER_WAIT_TIMEOUT
        # на страницу (десятки минут), хотя выглядело как "ждём максимум 60 с".
        page_deadline = time.time() + BUFFER_WAIT_TIMEOUT
        page_hard_deadline = time.time() + 5 * BUFFER_WAIT_TIMEOUT  # 25.09: страницы 3 МБ печатаются дольше 60 с
        for idx, packet in enumerate(page_bytes_packets):
            self.logger(f"=== пакет данных {idx+1}/{len(page_bytes_packets)}, {len(packet)} байт ===")
            r = self.write_command(0xa0, 0xe0, nread=1)
            if self.ack_status_change(r):
                r = self.write_command(0xa0, 0xe0, nread=1)
            status = Status(r[0] if r else b'')
            consecutive_empty_reads = 0 if (r and r[0]) else 1
            stall_checks = 0
            while status.buffer_full:
                if time.time() > page_deadline:
                    notify("Canon LBP-1120", tr(
                        "Принтер завис при печати. Проверьте бумагу/крышку и выключите/включите питание.",
                        "The printer stalled while printing. Check paper/cover and power-cycle it."))
                    raise TimeoutError(
                        f"Принтер {BUFFER_WAIT_TIMEOUT} с не освобождает буфер (пакет {idx+1}/{len(page_bytes_packets)}). "
                        "Возможно, принтер в ошибке (нет бумаги, замятие, крышка): проверьте его и выключите/включите питание.")
                # S2: пустой ответ на статус-запрос (dev.read() кинул USBError
                # внутри write_command) НЕСКОЛЬКО раз подряд - явный признак, что
                # устройство физически пропало (отключили USB), а не просто "буфер
                # полон" (у последнего всегда приходит содержательный ответ >=5 байт).
                # Не ждём молча полный BUFFER_WAIT_TIMEOUT - отказываем сразу.
                if consecutive_empty_reads >= 5:
                    notify("Canon LBP-1120", tr(
                        "Принтер пропал во время печати (отключили USB?). Проверьте подключение и повторите печать.",
                        "The printer disappeared during printing (USB unplugged?). Check the connection and print again."))
                    raise usb.core.USBError(
                        f"Устройство не отвечает {consecutive_empty_reads} запросов подряд (пакет {idx+1}/{len(page_bytes_packets)}) - "
                        "похоже, физически отключено или переустановлено Windows.")
                # Раз в секунду (каждые ~10 итераций по 0.1 с) спрашиваем a0a0, чтобы
                # при реальной ошибке (замятие/крышка) отказать сразу с точной причиной,
                # а не ждать полный BUFFER_WAIT_TIMEOUT с общим сообщением "принтер завис".
                stall_checks += 1
                if stall_checks % 10 == 0:
                    flags = parse_error_flags(self.write_command(0xa0, 0xa0, nread=2))
                    if flags and (flags["no_cartridge"] or flags["jam"] or flags["cover_open"]):
                        msg = error_flags_message(flags)
                        notify("Canon LBP-1120", msg)
                        raise RuntimeError(msg)
                self.logger("  буфер полон, жду...")
                time.sleep(0.1)
                r = self.write_command(0xa0, 0xe0, nread=1)
                if self.ack_status_change(r):
                    r = self.write_command(0xa0, 0xe0, nread=1)
                status = Status(r[0] if r else b'')
                consecutive_empty_reads = consecutive_empty_reads + 1 if not (r and r[0]) else 0

            # 02.10.2026: пакет уходит одной bulk-передачей, без пауз между кусками по 4 КБ.
            # Принтер тянет лист с постоянной скоростью и не ждёт данных: при ~125 КБ/с
            # (паузы 16 мс на каждые 4 КБ) плотные страницы 0,9-1,4 МБ обрывались на
            # середине листа (лог 30.09: в обрезанных заданиях принтер ни разу не сообщал
            # "буфер полон" - тормозила отправка). Ждём только по биту буфера выше.
            self.dev.write(self.ep_out.bEndpointAddress, packet, timeout=10000)
            self.logger(f"  data write {len(packet)} (one transfer)")
            # принтер принял пакет - значит идёт печать: дедлайн простоя отсчитывается заново,
            # но не дальше общего потолка на страницу
            page_deadline = min(time.time() + BUFFER_WAIT_TIMEOUT, page_hard_deadline)

        self.write_command(0xa0, 0xe0, nread=1)
        self.write_command(0xa2, 0xd0, nread=0)
        self.write_command(0xa0, 0xe0, nread=1)
        self.write_command(0xa1, 0xa0, nread=2)

        self.logger("=== страница отправлена ===")
        is_810 = (self.dev.idProduct == PRODUCT_ID_810)
        if wait_done:
            self.wait_until_done()
        if True:   # 14.10.2026: проверка «лист вышел» теперь и у 1120 (раньше только у 810), биты a0a0 у обеих моделей одинаковы
            # 13.10.2026: принтер отвечает "страницу закончил" и когда лист застрял (новый картридж
            # №1 не пускал лист к барабану). Лист засчитываем только если после печати нет
            # замятия и крышка закрыта; иначе пишем в лог и сообщаем пользователю. Не бросаем
            # исключение: повторная отправка при замятии дала бы лишнюю страницу после сброса.
            flags = parse_error_flags(self.write_command(0xa0, 0xa0, nread=2)) if wait_done else None
            if flags and (flags["jam"] or flags["cover_open"]):
                msg = error_flags_message(flags)
                self.logger(f"=== ЛИСТ НЕ ВЫШЕЛ, в счётчик не засчитан: {msg} ===")
                notify("Canon LBP-810" if is_810 else "Canon LBP-1120", tr(
                    "Страница не вышла из принтера. ", "The page did not come out of the printer. ") + msg)
            else:
                _count_sheet(self.logger, is_810=is_810)


def print_with_retry(packets, max_retries: int = 2, retry_wait: float = 2.0,
                      logger=print, wait_done: bool = True) -> None:
    """
    Печать одной страницы с автоматическим повтором при сбое подачи (07.10.2026, см.
    память lbp1120_printer_status_bits.md). Проверено живьём дважды: если во время захвата
    листа его задели рукой, принтер перестаёт принимать данные до конца USB-сессии - ни
    ожидание, ни возврат листа это не лечит. У протокола нет "продолжить с прерванного
    места" - помогает только полностью новое подключение (Printer() заново) и повторная
    отправка страницы ЦЕЛИКОМ. Эта функция и делает ровно это автоматически, вместо того
    чтобы прерывать задание с Traceback.

    Повторяются RuntimeError (нет картриджа/замятие/крышка/подача - см. error_flags_message)
    и TimeoutError (зависший буфер, таймаут ожидания бумаги). usb.core.USBError (устройство
    физически пропало) НЕ повторяется - переподключение тут не поможет, пока не вернут кабель.

    max_retries - сколько раз всего пытаться печатать (1 - вообще без повтора, 2 - одна
    повторная попытка). Если все попытки исчерпаны - поднимает последнюю ошибку как есть.
    """
    last_exc = None
    for attempt in range(1, max_retries + 1):
        printer = None
        try:
            with DeviceLock():
                printer = Printer(logger=logger)
                printer.print_page(packets, first_page=True, wait_done=wait_done)
            return
        except (RuntimeError, TimeoutError) as e:
            last_exc = e
            if printer is not None:
                # Без этого вторая попытка открыть то же USB-устройство ловит
                # "Access denied" - предыдущий Printer() не освободил его сам
                # (проверено живьём 07.10.2026: ValueError/Access denied на retry).
                try:
                    usb.util.dispose_resources(printer.dev)
                except Exception:  # noqa: BLE001 - лишь бы не сорвать повтор
                    pass
            if attempt >= max_retries:
                break
            logger(f"  Сбой подачи (попытка {attempt}/{max_retries}): {e}")
            notify("Canon LBP-1120", tr(
                f"Сбой при печати, повторяю попытку {attempt + 1} из {max_retries}...",
                f"Printing failed, retrying attempt {attempt + 1} of {max_retries}..."))
            time.sleep(retry_wait)
    raise last_exc


def main():
    if os.environ.get("CAPT_STRIPES") == "1":
        print("Сжимаю тестовую страницу с чёрно-белыми полосами...")
        packets = compress_page(make_stripe_pattern_source(stripe_height=200))
    else:
        print("Сжимаю тестовую белую страницу...")
        packets = compress_blank_page()
    total = sum(len(p) for p in packets)
    print(f"Готово: {len(packets)} пакет(ов), всего {total} байт")

    with DeviceLock():
        p = Printer()
        p.print_page(packets, first_page=True)
    print("Готово.")


if __name__ == "__main__":
    main()
