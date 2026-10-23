"""
Печать PDF-файла на Canon LBP-1120 через WinUSB.

Использование:
    python capt_print_pdf.py файл.pdf [номер_страницы] [--dithering РЕЖИМ]

Режимы (--dithering):
    floyd-steinberg  гладкие полутона (по умолчанию, ~1 сек на страницу)
    ordered          паттерны Байера 4x4: чёткий текст, полутона со "ступеньками"
    threshold        чёрное/белое без полутонов

Страница рендерится сразу в разрешение движка принтера (4736x6968 пикселей
при 600dpi, см. LINE_SIZE/LINES_BY_PAGE в capt_print2.py) и вписывается по
центру без искажения пропорций. Буфер принтера физически книжный - другой
физической формы листа этот принтер не производит никогда (узкая печатающая
головка, не аппаратный выбор). Для альбомных страниц (шире, чем выше)
содержимое ВСЕГДА разворачивается на 90°, чтобы занять лист целиком (решение
пользователя 23.09.2026, см. AUDIT_2026-09-22.md) - после печати лист нужно
физически повернуть на 90°, чтобы прочитать. Если даже самый жёсткий режим
деградации не помещается в память принтера - честный отказ (см. prepare_page),
а не урезанная по площади печать без поворота: вариант "без поворота"
неудачно приводил к путанице ("это книжная?"/"это альбомная?") и убран.
"""
import os
import sys
import pypdfium2 as pdfium  # рендер PDF (ранее PyMuPDF/AGPL, заменён 06.10.2026)
from PIL import Image, ImageChops, ImageFilter

import capt_print2 as _c2
from capt_print2 import (
    LINE_SIZE, LINES_BY_PAGE, Printer, DeviceLock, compress_page, notify, tr,
    SETTINGS,
)

# Штамп "Sr. No. <серийник>" в конце строки заголовка install_test_page.pdf (07.10.2026).
# Ставится только когда явно включено (см. set_install_stamp_serial) - обычная печать не
# трогает. Не диагностика (в отличие от diag_stamp.py/QR) - часть самого тест-листа
# установщика, идёт в exe. Координаты геометрии заголовка - из make_install_test_page.py:
# text(10, 16, "ТЕСТ ПЕЧАТИ Canon LBP-1120", 20, "arb").
_INSTALL_STAMP_SERIAL = None
_INSTALL_STAMP_MODEL = "LBP-1120"


def set_install_stamp_serial(serial: str | None, model: str = "LBP-1120") -> None:
    global _INSTALL_STAMP_SERIAL, _INSTALL_STAMP_MODEL
    _INSTALL_STAMP_SERIAL = serial
    _INSTALL_STAMP_MODEL = model


def _stamp_sr_no(canvas: Image.Image, left: int, top: int, zoom: float, logger=print) -> None:
    serial = _INSTALL_STAMP_SERIAL
    if not serial:
        return
    from PIL import ImageDraw, ImageFont
    MM = 72 / 25.4
    font_px = round(20 * zoom)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", font_px)
    except OSError:
        logger("  Sr.No.: шрифт arialbd.ttf не найден, штамп пропущен")
        return
    draw = ImageDraw.Draw(canvas)
    title = tr(f"ТЕСТ ПЕЧАТИ Canon {_INSTALL_STAMP_MODEL}", f"PRINT TEST Canon {_INSTALL_STAMP_MODEL}")   # как на листе (make_install_test_page.py)
    title_x = 10 * MM * zoom - left
    title_y = 16 * MM * zoom - top          # baseline, как insert_text в make_install_test_page.py
    title_w = draw.textlength(title, font=font)
    gap_px = 6 * MM * zoom                  # ~6 мм отступ от конца заголовка
    x = title_x + title_w + gap_px
    draw.text((x, title_y), f"Sr. No. {serial}", font=font, fill=0, anchor="ls")
    logger(f"  Sr.No. {serial} допечатан в заголовок (x={x:.0f}, y={title_y:.0f})")

# Разрешение печати движка: 600 dpi (592 байта/строка = 4736 px) или 300 dpi
# (296 байт/строка = 2368 px); переключается settings.ini -> capt_print2.apply_resolution().
# Размеры читаются из capt_print2 при каждом вызове, а не запоминаются при импорте.
def _dpi():
    return _c2.RESOLUTION_DPI


def _pixel_width():
    return _c2.LINE_SIZE * 8


def _pixel_height():
    return _c2.LINES_BY_PAGE


DPI = 600
PIXEL_WIDTH = LINE_SIZE * 8   # 4736 (значение для 600 dpi, для справки)
PIXEL_HEIGHT = LINES_BY_PAGE  # 6968

THRESHOLD = 200  # порог серого для режима threshold (0-255): пиксель темнее порога -> чёрный.
# 128 съедал светло-серый мелкий текст (адреса, надписи в макетах); 200 его сохраняет,
# а светлый шум JPEG-фона (ярче ~225) всё равно остаётся белым.

DEFAULT_DITHERING = "floyd-steinberg"
DITHERING_MODES = ("floyd-steinberg", "floyd12", "smart", "smart2", "ordered8", "ordered", "screen", "threshold")  # от гладкого к самому лёгкому

# Максимум сжатых данных на страницу, байт. Калибровано печатью 22.09.2026 на макете
# "Сулугуни" (прямой PDF, без прохода через Word): 505 КБ (ordered+blur3) вышло ЦЕЛИКОМ,
# 599 КБ (ordered+blur2) обрезалось почти полностью (вышел только маленький фрагмент внизу).
# Реальный предел принтера где-то между ними. Поднято с 520 до 540 КБ 23.09.2026:
# реальная плотная накладная упиралась в шаг threshold(128,blur4.5)=521 669 байт -
# промахивалась мимо 520 КБ всего на 1,7 КБ и проваливалась сразу на разрушительный
# blur4.75 (эффект обвала - см. THRESHOLD_BLUR_STEPS). 540 КБ ловит такие
# "чуть-чуть не уместившиеся" случаи, остаётся заметно ниже подтверждённо
# проблемных 599 КБ.
# 24.09.2026: "предел ~512 КБ" оказался следствием кусков по 63 КБ (принтер сообщает
# "буфер не полон" при свободных <63 КБ). С кусками <= PACKET_LIMIT (32 КБ, как у родного
# драйвера) печатаются целиком: повёрнутая накладная 660 КБ, "Сулугуни" 840 КБ (оба
# раньше упирались в лимит и падали на threshold/обрыв); родной драйвер в режиме Smooth
# отправляет 2,1 МБ. Верхняя граница взята с запасом над этим значением.
# 02.10.2026: после ускорения отправки (capt_print2: пакет одной передачей) проверено
# на сертификате-скане: 1,72 МБ (ordered) - целиком, 3,39 МБ (smart) - обрыв на ~85%
# (принтер сам не успевает, флаг 0x02 в a0a0). Лимит = 2,1 МБ, как у родного драйвера.
PAGE_BUDGET = 2_100_000


def _budget_override(default: int) -> int:
    """Тестовый режим: файл budget.txt рядом с программой (одно число - байт) заменяет
    PAGE_BUDGET. Нужен, чтобы проверить гипотезу 24.09.2026: предел "~512 КБ" на самом
    деле вызван кусками по 63 КБ, а не размером страницы (родной драйвер шлёт до 2 МБ
    кусками <=32 КБ). Без файла поведение прежнее."""
    try:
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        with open(os.path.join(base, "budget.txt"), encoding="ascii") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return default


PAGE_BUDGET = _budget_override(PAGE_BUDGET)

# Паттерн Байера 4x4. Пороги лежат строго МЕЖДУ 0 и 255: на значениях 0/255
# чисто белые/чёрные пиксели инвертировались бы и давали сетку "грязи".
BAYER_4X4 = [
    [8, 136, 40, 168],
    [200, 72, 232, 104],
    [56, 184, 24, 152],
    [248, 120, 216, 88],
]

# Растр 8x8 (кластерные точки, 64 уровня серого) - восстановлен по USB-дампу родного
# драйвера Canon (24.09.2026: печать рампы и клина серого известных значений,
# usb_dumps/08_photo_default.pcapng, пороги оценены по точке переключения пикселя
# вдоль рампы и приведены к 64 равномерным уровням). Данные страницы с ним
# и мельче, и с большим числом уровней серого, чем у Байера 4x4.


def _bayer(n: int) -> list[list[int]]:
    """Индексы матрицы Байера n x n (n - степень двойки), 0..n*n-1."""
    if n == 1:
        return [[0]]
    m, h = _bayer(n // 2), n // 2
    return [[4 * m[y % h][x % h] + ((0, 2), (3, 1))[y // h][x // h] for x in range(n)] for y in range(n)]


# Байер 8x8 (02.10.2026): 65 уровней серого вместо 17 у 4x4 - после компенсации тонов
# 4x4 давал на фото "плакатные" плоские пятна; данных почти столько же (фото 261 КБ против
# 219 КБ), поэтому стоит в цепочке сразу после smart.
BAYER_8X8 = [[int((v + 0.5) * 256 / 64) for v in row] for row in _bayer(8)]

SCREEN_8X8 = [
    [233, 193, 49, 21, 5, 65, 169, 225],
    [185, 137, 121, 89, 53, 97, 129, 177],
    [73, 105, 153, 217, 209, 145, 113, 41],
    [13, 33, 161, 253, 241, 201, 81, 17],
    [1, 69, 173, 229, 237, 197, 57, 29],
    [61, 101, 133, 181, 189, 141, 125, 93],
    [213, 149, 117, 45, 77, 109, 157, 221],
    [245, 205, 85, 25, 9, 37, 165, 249],
]


def _render_rgb(page, scale: float) -> Image.Image:
    """RGB-растр страницы pypdfium2 (замена PyMuPDF get_pixmap, 06.10.2026). scale - пикселей на пункт."""
    rot = 180 if SETTINGS.get("rotate180") else 0   # поворот содержимого страницы на 180 (размер страницы тот же)
    return page.render(scale=scale, rotation=rot, may_draw_forms=True).to_pil().convert("RGB")


def _to_gray(img: Image.Image) -> Image.Image:
    """RGB -> серый "L" (14.10.2026). classic: PIL (0,299 R + 0,587 G + 0,114 B), как раньше. luminance (gray_conversion):
    световая яркость как у Windows в режиме "Чёрно-белая печать": линеаризация гаммой 2,2, веса 0,2126/0,7152/0,0722,
    обратная гамма. Считается кусками по строкам (страница 600 dpi - 35 млн пикселей)."""
    if SETTINGS.get("gray_conversion") != "luminance" or img.mode == "L":
        return img.convert("L")
    import numpy as np
    rgb = img.convert("RGB")
    a = np.asarray(rgb)
    lin = (np.arange(256, dtype=np.float32) / 255.0) ** 2.2
    out = np.empty(a.shape[:2], dtype=np.uint8)
    step = 256
    for y in range(0, a.shape[0], step):
        c = a[y:y + step]
        yv = 0.2126 * lin[c[..., 0]] + 0.7152 * lin[c[..., 1]] + 0.0722 * lin[c[..., 2]]
        out[y:y + step] = np.clip(np.rint((yv ** (1.0 / 2.2)) * 255.0), 0, 255).astype(np.uint8)
    return Image.fromarray(out, "L")


def _render_true_size_canvas(page, page_w_pt, page_h_pt, landscape, logger):
    """
    Не-A4 лист (A5 и "свой размер", см. capt_print2.apply_paper_geometry): страница рисуется в
    ИСТИННОМ размере 1:1 (без вписывания и сжатия), альбомная разворачивается на 90° (лист у принтера
    всегда книжный). Первая строка растра принтер печатает на TOP_OFFSET_PX (~5мм) ниже переднего
    края листа, поэтому верхние TOP_OFFSET_PX строк страницы отрезаются (там всё равно не напечатать),
    а холст = LINE_SIZE*8 x LINES_BY_PAGE. Полоса CONTENT_MARGIN_MM у левого, правого и нижнего края
    листа остаётся белой (запас от самого края, по просьбе пользователя 28.09.2026).
    """
    paper_w_px, paper_h_px = _c2._PAGEPARMS_GEOM[2], _c2._PAGEPARMS_GEOM[3]
    zoom = paper_w_px / min(page_w_pt, page_h_pt)          # пикселей на пункт: короткая сторона = ширина листа
    pix = _render_rgb(page, zoom)
    gray = _to_gray(pix)
    if landscape:
        gray = gray.rotate(90, expand=True)  # PIL: исходный X=max -> верх листа
    logger(f"  Отрендерено 1:1: {pix.width}x{pix.height} px (страница {page_w_pt:.0f}x{page_h_pt:.0f} pt"
           f"{', альбомная -> поворот 90°' if landscape else ''}), лист {paper_w_px}x{paper_h_px} px")

    target_w, target_h = _pixel_width(), _pixel_height()
    top = _c2.TOP_OFFSET_PX
    # LBP-810 + экономия: строка уже листа и стоит по центру (поля NATIVE810_MARGIN_PX), берём центральное окно страницы
    left = max(0, (paper_w_px - target_w) // 2) if _c2.native810_geom() else 0
    canvas = Image.new("L", (target_w, target_h), 255)
    crop = gray.crop((left, top, min(gray.width, left + target_w), min(gray.height, top + target_h)))
    canvas.paste(crop, (0, 0))

    m = round(_c2.CONTENT_MARGIN_MM / 25.4 * _dpi())
    if m > 0:
        from PIL import ImageDraw
        d = ImageDraw.Draw(canvas)
        d.rectangle([0, 0, m - 1, target_h], fill=255)                  # слева
        d.rectangle([target_w - m, 0, target_w, target_h], fill=255)    # справа
        d.rectangle([0, target_h - m, target_w, target_h], fill=255)    # снизу
    _stamp_sr_no(canvas, left, top, zoom, logger)
    return canvas


def _render_a4_true_size_canvas(page, page_w_pt, page_h_pt, landscape, logger):
    """
    Страница A4 (210x297) в ИСТИННОМ размере 1:1, без вписывания и сжатия (решение пользователя 01.10.2026:
    раньше A4 вписывалась в холст 4736 px и печаталась в масштабе ~95,5%). Байты a0d0 для A4 не меняются:
    канва PIXEL_WIDTH x PIXEL_HEIGHT стоит по центру листа (в a0d0 margin_px = (4960-4736)/2 = 112 px @600 dpi)
    и начинается TOP_OFFSET_PX (аппаратные ~5 мм) ниже переднего края листа. Поэтому из страницы берётся окно:
    по горизонтали центральные PIXEL_WIDTH px (~4,7 мм слева и справа не печатаются), по вертикали - со
    строки TOP_OFFSET_PX. Альбомная A4 разворачивается на 90° (лист у принтера всегда книжный).
    """
    dpi = _dpi()
    zoom = dpi / 72.0
    pix = _render_rgb(page, zoom)
    gray = _to_gray(pix)
    if landscape:
        gray = gray.rotate(90, expand=True)  # PIL: исходный X=max -> верх листа
    target_w, target_h = _pixel_width(), _pixel_height()
    paper_w = round(210 / 25.4 * dpi)
    left = max(0, (paper_w - target_w) // 2)
    top = round(_c2.TOP_OFFSET_PX * dpi / 600)
    logger(f"  Отрендерено 1:1 (A4): {pix.width}x{pix.height} px (страница {page_w_pt:.0f}x{page_h_pt:.0f} pt"
           f"{', альбомная -> поворот 90°' if landscape else ''}), окно печати x {left}..{left + target_w}, строки с {top}")
    canvas = Image.new("L", (target_w, target_h), 255)
    crop = gray.crop((left, top, min(gray.width, left + target_w), min(gray.height, top + target_h)))
    canvas.paste(crop, (0, 0))
    m = round(_c2.CONTENT_MARGIN_MM / 25.4 * dpi)
    if m > 0:
        from PIL import ImageDraw
        sheet_rows = round(297 / 25.4 * dpi) - top          # строк листа ниже аппаратного отступа
        ImageDraw.Draw(canvas).rectangle([0, sheet_rows - m, target_w, target_h], fill=255)  # снизу
    _stamp_sr_no(canvas, left, top, zoom, logger)
    return canvas


def _render_gray_canvas(pdf_path: str, page_num: int, logger=print, rotate_landscape: bool = True) -> Image.Image:
    """
    Страница PDF в градациях серого на белом холсте PIXEL_WIDTH x PIXEL_HEIGHT.

    Буфер движка принтера физически книжный (PIXEL_WIDTH < PIXEL_HEIGHT) -
    аппаратного поворота нет, и другой физической формы листа принтер не
    производит никогда. Альбомные страницы (шире, чем выше) ВСЕГДА
    разворачиваются на 90°, чтобы занять лист целиком (финальное решение
    пользователя 23.09.2026, см. AUDIT_2026-09-22.md) - лист после печати
    нужно физически повернуть на 90°, чтобы прочитать. Промежуточный
    вариант "без поворота, лист не на всю высоту" пробовали и убрали -
    путал при обсуждении ("это книжная или альбомная?").

    rotate_landscape=False отключает поворот (используется редко - код
    рабочий, оставлен на случай локальной диагностики).
    """
    doc = pdfium.PdfDocument(pdf_path)
    if page_num >= len(doc):
        raise ValueError(f"В PDF только {len(doc)} страниц(ы), запрошена #{page_num + 1}")
    page = doc[page_num]

    page_w_pt, page_h_pt = page.get_width(), page.get_height()
    landscape = page_w_pt > page_h_pt and rotate_landscape

    if _c2._PAGEPARMS_GEOM is not None:
        return _render_true_size_canvas(page, page_w_pt, page_h_pt, landscape, logger)
    if getattr(_c2, "A4_TRUE_SIZE", False):
        return _render_a4_true_size_canvas(page, page_w_pt, page_h_pt, landscape, logger)

    target_w, target_h = (_pixel_height(), _pixel_width()) if landscape else (_pixel_width(), _pixel_height())

    margin_px = 0
    fit_w, fit_h = max(1, target_w - 2 * margin_px), max(1, target_h - 2 * margin_px)

    zoom_x = (fit_w / _dpi() * 72) / page_w_pt
    zoom_y = (fit_h / _dpi() * 72) / page_h_pt
    zoom = min(zoom_x, zoom_y)  # вписываем без искажения пропорций

    scale = zoom * _dpi() / 72
    # 29.09.2026: рендерим в RGB и переводим в серый сами (PIL "L" = 0.299R+0.587G+0.114B).
    # fitz.csGRAY считает ЛИНЕЙНУЮ яркость (Rec.709 в линейном свете) - насыщенные цвета
    # уходят гораздо светлее эталона (красный 126 вместо 76, зелёный 219 вместо 150, жёлтый
    # 246 вместо 226) и почти пропадают в белом. Классическая формула совпала с предпросмотром
    # печати в градациях серого на всех 12 тестовых цветах (color_test.pdf, замер 29.09.2026).
    pix = _render_rgb(page, scale)
    logger(f"  Отрендерено: {pix.width}x{pix.height} px (страница {page_w_pt:.0f}x{page_h_pt:.0f} pt"
           f"{', альбомная -> поворот 90°' if landscape else ''})")

    gray = _to_gray(pix)
    canvas = Image.new("L", (target_w, target_h), 255)
    offset_x = max(0, (target_w - pix.width) // 2)
    offset_y = max(0, (target_h - pix.height) // 2)
    canvas.paste(gray, (offset_x, offset_y))
    if landscape:
        canvas = canvas.rotate(90, expand=True)  # (target_w,target_h) -> (PIXEL_WIDTH,PIXEL_HEIGHT)
    return canvas


def _ordered_dither(canvas: Image.Image, matrix=None) -> Image.Image:
    """Ordered dithering по матрице порогов (по умолчанию Байер 4x4) без попиксельных циклов Python."""
    matrix = matrix or BAYER_4X4
    n = len(matrix)
    width, height = canvas.size
    rows = [bytes(matrix[y][x % n] for x in range(width)) for y in range(n)]
    thresholds = Image.frombytes(
        "L", canvas.size, b"".join(rows[y % n] for y in range(height)))
    # canvas - threshold > 0  <=>  пиксель светлее порога -> белый
    white = ImageChops.subtract(canvas, thresholds).point(lambda v: 255 if v > 0 else 0)
    return white.convert("1", dither=Image.Dither.NONE)


# Режим "smart" (29.09.2026): один принтер для текста и фото. Страница режется на блоки
# SMART_BLOCK x SMART_BLOCK px (48 px ~ 2мм при 600dpi); блок, где доля полутонов
# (SMART_MID_LO..SMART_MID_HI из 255) >= SMART_MID_FRACTION, - фото/градиент/тоновая заливка:
# для него плавный Флойд-Стейнберг; остальное (текст, линии, чистые чёрный/белый) - Байер 4x4
# (чётче края). У текста полутона только в сглаживании краёв (единицы % блока), у фото - десятки %.
# Маска расширяется на соседние блоки, чтобы граница режимов не резала край фото.
SMART_BLOCK = 48
SMART_MID_LO, SMART_MID_HI = 20, 240
SMART_MID_FRACTION = 0.30


def _photo_mask(canvas: Image.Image, fraction: float = None):
    """Возвращает (маска "L" 255=плавный режим, доля страницы под плавным режимом)."""
    import numpy as np
    a = np.asarray(canvas)
    h, w = a.shape
    B = SMART_BLOCK
    hb, wb = -(-h // B), -(-w // B)
    pad = np.pad(a, ((0, hb * B - h), (0, wb * B - w)), constant_values=255)
    mid = (pad >= SMART_MID_LO) & (pad <= SMART_MID_HI)
    photo = mid.reshape(hb, B, wb, B).mean(axis=(1, 3)) >= (SMART_MID_FRACTION if fraction is None else fraction)
    grown = photo.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            shifted = np.zeros_like(photo)
            ys = slice(max(dy, 0), hb + min(dy, 0))
            yd = slice(max(-dy, 0), hb + min(-dy, 0))
            xs = slice(max(dx, 0), wb + min(dx, 0))
            xd = slice(max(-dx, 0), wb + min(-dx, 0))
            shifted[yd, xd] = photo[ys, xs]
            grown |= shifted
    mask = np.repeat(np.repeat(grown, B, axis=0), B, axis=1)[:h, :w]
    return Image.fromarray(mask.astype(np.uint8) * 255, "L"), float(grown.mean())


SMART2_FINE_FROM = 190   # тон (после _TONE_LUT), с которого smart2 печатает фото точкой 1x1
SMART2_FINE_SOFT = 10    # ширина плавного перехода между точками 1x1 и 2x2 (+- от порога)


def _floyd_cells(canvas: Image.Image, cx: int, cy: int) -> Image.Image:
    """Флойд-Стейнберг точками cx x cy px (05.10.2026). 1x2 - горизонталь 600 dpi, вертикаль 300 dpi: строки идут парами
    одинаковыми, v1 пропускает вторую строку пары целиком (0x41), данные вдвое меньше, чем у 1x1, при мелком зерне."""
    w, h = canvas.size
    small = canvas.resize((max(1, w // cx), max(1, h // cy)), Image.BOX)
    dots = small.convert("1", dither=Image.Dither.FLOYDSTEINBERG).resize((small.width * cx, small.height * cy), Image.NEAREST)
    out = Image.new("1", (w, h), 1)
    out.paste(dots, (0, 0))
    return out


def _floyd_coarse(canvas: Image.Image, cell: int = 2) -> Image.Image:
    """Флойд-Стейнберг точками cell x cell px (02.10.2026): плавно, без сетки Байера, но данных
    в 2-3 раза меньше, чем у обычного floyd (фото: 0,9 МБ против 1,84 МБ) - успевает принтер."""
    w, h = canvas.size
    small = canvas.resize((max(1, w // cell), max(1, h // cell)), Image.BOX)
    dots = small.convert("1", dither=Image.Dither.FLOYDSTEINBERG).resize(
        (small.width * cell, small.height * cell), Image.NEAREST)
    out = Image.new("1", (w, h), 1)
    out.paste(dots, (0, 0))
    return out


def _smart_dither(canvas: Image.Image, logger=print, coarse: bool = False,
                  coarse_canvas: Image.Image = None) -> Image.Image:
    """coarse=True (режим smart2): фото-участки - _floyd_coarse вместо обычного floyd,
    по coarse_canvas (та же страница со своей кривой тонов), если он задан."""
    mask, share = _photo_mask(canvas)
    logger(f"  smart: плавный режим на {share * 100:.0f}% площади (фото/тона), остальное - чёткий")
    if share <= 0.0:
        return _ordered_dither(canvas)
    if coarse:
        # 02.10.2026: точки 2x2 на светлом фоне видны отдельными пятнами (замечание по скану
        # стены на фото) - светлые участки (тон >= SMART2_FINE_FROM после кривой) печатаются
        # обычным floyd 1x1, средние/тёмные - 2x2. Фото: 1,28 МБ, плотность в норме.
        fine = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")
        rough = _floyd_coarse(coarse_canvas if coarse_canvas is not None else canvas).convert("L")
        # Граница "1x1 / 2x2" по резкому порогу давала на ровной стене пятна другой фактуры -
        # в полосе SMART2_FINE_FROM +- SMART2_FINE_SOFT выбор случайный с плавным перевесом.
        import numpy as np
        a = np.asarray(canvas, dtype=np.int16)
        rng = np.random.default_rng(12345)
        noise = rng.integers(-SMART2_FINE_SOFT, SMART2_FINE_SOFT + 1, size=a.shape, dtype=np.int16)
        light = Image.fromarray(((a + noise) >= SMART2_FINE_FROM).astype(np.uint8) * 255, "L")
        del a, noise
        smooth1 = Image.composite(fine, rough, light).convert("1", dither=Image.Dither.NONE)
    else:
        smooth1 = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    if share >= 1.0 and not coarse:
        return smooth1
    smooth = smooth1.convert("L")
    crisp = _ordered_dither(canvas).convert("L")
    if coarse:
        # 02.10.2026: в smart2 блоки 48 px целиком уходили в точки 2x2 вместе с попавшими в них
        # тонкими линиями и буквами (тест-лист: линии таблицы рядом с серыми заливками и подпись
        # над градиентом "рассыпались"). Теперь плавный режим - только внутри сплошных полутоновых
        # участков: полутоновый пиксель, вокруг которого (5x5) тоже только полутона; чёрное,
        # белое, линии и края букв - чётким режимом.
        mid = canvas.point(lambda v: 255 if SMART_MID_LO <= v <= SMART_MID_HI else 0).filter(ImageFilter.MinFilter(5))
        mask = ImageChops.multiply(mask, mid)
    return Image.composite(smooth, crisp, mask).convert("1", dither=Image.Dither.NONE)


def _apply_brightness_contrast(canvas: Image.Image, brightness: int, contrast: int) -> Image.Image:
    """Яркость и контраст из settings.ini (проценты -100..100), до растрирования - как у
    родного драйвера это делается на стороне ПК (в параметрах страницы они не меняются)."""
    if not brightness and not contrast:
        return canvas
    factor = 1.0 + contrast / 100.0
    shift = brightness * 255 / 100.0
    lut = [max(0, min(255, int(round((v - 128) * factor + 128 + shift)))) for v in range(256)]
    return canvas.point(lut)


# Компенсация потемнения средних тонов (02.10.2026). Замер по шкале 16 ступеней тест-листа
# (сканы 600 dpi, A4 1:1, floyd-steinberg и ordered почти совпали - кривая по среднему):
# всё темнее ~40% (102/255) печаталось сплошным чёрным, серый 53% выходил как 21%.
# Пары (задано, вышло на бумаге) в шкале 0..255 после нормировки бумага/чёрный тонер.
_TONE_PRINTED = ((0, 0), (85, 1), (102, 6), (119, 22), (136, 47), (153, 100), (170, 148),
                 (187, 198), (204, 218), (221, 240), (238, 250), (255, 255))


def _tone_correction_lut() -> list[int]:
    """Обратная кривая: для нужного на бумаге тона v - какой тон подать принтеру.
    0 и 255 не меняются (чёрный текст остаётся чёрным, бумага белой)."""
    lut = []
    for v in range(256):
        for (n0, p0), (n1, p1) in zip(_TONE_PRINTED, _TONE_PRINTED[1:]):
            if p0 <= v <= p1:
                lut.append(int(round(n0 + (n1 - n0) * (v - p0) / (p1 - p0))) if p1 > p0 else n0)
                break
    lut[0] = 0
    return lut


_TONE_LUT = _tone_correction_lut()

# Крупные точки 2x2 (smart2) расплываются меньше, и _TONE_LUT для них пересветляет: замер шкалы
# тест-листа в smart2 с _TONE_LUT (02.10.2026, скан 10-09-24) - % белого на бумаге для ступеней
# 0, 7, 13 ... 100 %. Поправка поверх: X(v) = _TONE_LUT(P^-1(v)), P - эта кривая.
_COARSE_PRINTED_PCT = (0, 17, 20, 27, 29, 33, 36, 40, 44, 49, 54, 59, 62, 71, 80, 100)


def _coarse_tone_lut() -> list[int]:
    pts = [(i * 17, p * 255 / 100) for i, p in enumerate(_COARSE_PRINTED_PCT)]
    lut = []
    for v in range(256):
        for (n0, p0), (n1, p1) in zip(pts, pts[1:]):
            if p0 <= v <= p1:
                n = n0 + (n1 - n0) * (v - p0) / (p1 - p0) if p1 > p0 else n0
                lut.append(_TONE_LUT[min(255, int(round(n)))])
                break
    return lut


_TONE_LUT_COARSE = _coarse_tone_lut()

_BLEND_CACHE = {}


def _blend_lut(lut: list[int], strength: int) -> list[int]:
    """Поправка тонов с силой strength 0..100 %: смесь тождественной кривой и полной."""
    if strength >= 100:
        return lut
    key = (id(lut), strength)
    if key not in _BLEND_CACHE:
        _BLEND_CACHE[key] = [int(round(v + (lut[v] - v) * strength / 100.0)) for v in range(256)]
    return _BLEND_CACHE[key]


def _shift_canvas(canvas: Image.Image, logger=print) -> Image.Image:
    """Сдвиг печати на листе (settings.ini: shift_x_mm / shift_y_mm, для LBP-810 приоритет у shift810_*).
    X вправо, Y вниз; освободившийся край белый, вышедшее за лист обрезается."""
    x_mm, y_mm = SETTINGS.get("shift_x_mm") or 0.0, SETTINGS.get("shift_y_mm") or 0.0
    if _c2.is_810_mode():
        if SETTINGS.get("shift810_x_mm") is not None:
            x_mm = SETTINGS["shift810_x_mm"]
        if SETTINGS.get("shift810_y_mm") is not None:
            y_mm = SETTINGS["shift810_y_mm"]
    dx, dy = round(x_mm / 25.4 * _dpi()), round(y_mm / 25.4 * _dpi())
    if not dx and not dy:
        return canvas
    shifted = Image.new("L", canvas.size, 255)
    shifted.paste(canvas, (dx, dy))
    logger(f"  Сдвиг печати: {x_mm:+.1f} мм по X, {y_mm:+.1f} мм по Y ({dx:+d}, {dy:+d} px)")
    return shifted


TEXT_BLACK_BELOW = 160   # серый темнее этого вне фото становится чёрным (text_black)
THIN_DARK_BELOW = 150    # "тёмный" пиксель при поиске тонких линий (thin_lines)


def _text_and_lines(canvas: Image.Image, text_black: int, thin: int, logger=print) -> Image.Image:
    """Идеи из драйверов HP/Canon (13.10.2026). Работает на серой странице до полутонов и не трогает фото-участки
    (маска smart). text_black: тёмно-серое вне фото -> сплошной чёрный. thin: тонкие тёмные линии и мелкие штрихи
    (уже 3 px) утолщаются на thin px с каждой стороны."""
    import numpy as np
    # фото = блок 48 px, где полутона занимают >= 60% (у обычного smart порог 30%: мелкий серый текст туда попадает)
    photo, _share = _photo_mask(canvas, 0.6)
    nonphoto = np.asarray(photo) == 0
    a = np.asarray(canvas).copy()
    if text_black:
        a[nonphoto & (a < TEXT_BLACK_BELOW)] = 0
    if thin:
        dark = Image.fromarray(((a < THIN_DARK_BELOW) & nonphoto).astype(np.uint8) * 255, "L")
        opened = dark.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
        thin_px = ImageChops.subtract(dark, opened)
        grown = np.asarray(thin_px.filter(ImageFilter.MaxFilter(2 * thin + 1))) > 0
        a[grown & nonphoto] = 0
        logger(f"  Тонкие линии: утолщено {int(np.count_nonzero(np.asarray(thin_px)))} px на {thin} px")
    if text_black:
        logger("  Текст чёрным: серое темнее 160 вне фото -> чёрный")
    return Image.fromarray(a, "L")


def plan_manual_duplex(pages: list, reverse: bool = True):
    """Порядок страниц для ручного дуплекса. Возвращает (первый проход, второй проход, сколько пустых оборотов
    вставить в начало второго прохода). Нечётные страницы идут как есть; чётные - в обратном порядке, если
    reverse (стопка вышла лицевой стороной вниз и кладётся в лоток без перестановки). При reverse и нечётном
    числе страниц последний лист (страница n) остаётся с пустым оборотом: перед чётными вставляется 1 пустой оборот."""
    odd, even = pages[0::2], pages[1::2]
    pad = 0
    if reverse:
        even = even[::-1]
        if len(pages) % 2 == 1 and even:
            pad = 1
    return odd, even, pad


def make_blank_pdf(like_pdf: str, out_path: str) -> str:
    """Пустая белая страница того же размера, что страница 1 документа (для пустого оборота при ручном дуплексе)."""
    doc = pdfium.PdfDocument(like_pdf)
    w, h = doc[0].get_width(), doc[0].get_height()
    Image.new("L", (max(1, round(w)), max(1, round(h))), 255).save(out_path, "PDF", resolution=72.0)
    return out_path


def is_blank_page(pdf_path: str, page_num: int, threshold: int = 248) -> bool:
    """Страница целиком белая: на рендере 72 dpi нет ни одного пикселя темнее threshold.
    Любой знак препинания, тонкая линия или фоновая заливка делает страницу непустой (печатается)."""
    doc = pdfium.PdfDocument(pdf_path)
    page = doc[page_num]
    gray = _render_rgb(page, 1.0).convert("L")
    return gray.getextrema()[0] >= threshold


def render_page_to_bitmap(pdf_path: str, page_num: int = 0, dithering: str = DEFAULT_DITHERING,
                          threshold: int = None, blur: float = 0, logger=print,
                          rotate_landscape: bool = True) -> list[bytes]:
    """
    Рендерит страницу PDF в список строк растра: PIXEL_HEIGHT строк по
    LINE_SIZE байт (1 бит на пиксель, 1=чёрный, MSB-first).
    blur: радиус GaussianBlur перед dithering - только для "ordered" (для
    floyd-steinberg размытие УВЕЛИЧИВАЕТ объём сжатых данных, проверено).
    Сглаживает шум JPEG-сканов, снижая объём данных ordered-режима почти
    вдвое ценой лёгкой мягкости паттерна Байера - см. THRESHOLD_STEPS ниже.
    logger: см. prepare_page() - при печати через Redmon (S12) идёт в файл
    лога, а не в непрочитанный stdout процесса.
    rotate_landscape: см. _render_gray_canvas().
    """
    if dithering not in DITHERING_MODES:
        raise ValueError(f"Неизвестный режим dithering: {dithering} (доступны: {', '.join(DITHERING_MODES)})")

    canvas = _render_gray_canvas(pdf_path, page_num, logger=logger, rotate_landscape=rotate_landscape)
    canvas = _shift_canvas(canvas, logger)
    canvas = _apply_brightness_contrast(canvas, SETTINGS["brightness"], SETTINGS["contrast"])
    if SETTINGS.get("text_black") or SETTINGS.get("thin_lines"):
        canvas = _text_and_lines(canvas, int(SETTINGS.get("text_black") or 0), int(SETTINGS.get("thin_lines") or 0), logger)
    coarse_canvas = canvas   # для smart2: фото-участки точками 2x2 - своя кривая тонов
    if SETTINGS.get("tone_correction", 1) and dithering != "threshold":
        _st = int(SETTINGS.get("tone_strength", 50))
        coarse_canvas = canvas.point(_blend_lut(_TONE_LUT_COARSE, _st))
        canvas = canvas.point(_blend_lut(_TONE_LUT, _st))
    if blur:
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=blur))
    logger(f"  Применяю {dithering}{f' (blur={blur})' if blur else ''}...")

    if dithering == "smart":
        white = _smart_dither(canvas, logger)
    elif dithering == "floyd12":
        white = _floyd_cells(canvas, 1, 2)
    elif dithering == "smart2":
        if blur:
            coarse_canvas = coarse_canvas.filter(ImageFilter.GaussianBlur(radius=blur))
        white = _smart_dither(canvas, logger, coarse=True, coarse_canvas=coarse_canvas)
    elif dithering == "floyd-steinberg":
        white = canvas.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    elif dithering == "ordered8":
        white = _ordered_dither(canvas, BAYER_8X8)
    elif dithering == "ordered":
        white = _ordered_dither(canvas)
    elif dithering == "screen":
        if _c2.saver_810_active():
            # LBP-810 + экономия (13.10.2026): принтер печатает ~27% от заданного, одиночные точки светов (<5% плотности)
            # не видны - в блике получался белый "остров" с контуром. Свет не светлее ~6% точек (порог 240 из SCREEN_8X8),
            # чистая бумага (>=254) остаётся белой.
            canvas = canvas.point(lambda v: v if v >= 254 else min(v, 240))
        white = _ordered_dither(canvas, SCREEN_8X8)
    else:
        limit = THRESHOLD if threshold is None else threshold
        white = canvas.point(lambda v: 255 if v >= limit else 0).convert("1", dither=Image.Dither.NONE)

    # DIAG-STAMP (только рабочая копия C:\CaptPrinter, не в установщик): QR-метка с настройками
    try:
        import diag_stamp
        if diag_stamp.enabled():
            white = diag_stamp.stamp(white, {
                "mode": _chain_step_name(dithering, threshold, blur), "rot": int(rotate_landscape),
                "tone": SETTINGS.get("tone_correction", 1), "tstr": SETTINGS.get("tone_strength", 50), "v2": int(getattr(_c2, "USE_V2", False)), "br": SETTINGS["brightness"], "ct": SETTINGS["contrast"],
                "res": SETTINGS["resolution"], "ht": SETTINGS["halftone"], "td": SETTINGS["toner_density"],
                "ts": SETTINGS["toner_saver"], "rf": SETTINGS["refinement"], "bud": PAGE_BUDGET,
                "dens": [DENSITY_RATE_PER_10MM, DENSITY_BACKLOG_MAX],
            }, logger)
    except ImportError:
        pass

    raw = ImageChops.invert(white).tobytes()  # в режиме "1" строки выровнены по байту: ровно LINE_SIZE
    line = _c2.LINE_SIZE
    lines = [raw[i * line:(i + 1) * line] for i in range(_pixel_height())]
    return lines


THRESHOLD_STEPS = (200, 180, 160, 140, 128)  # от светлого (виден мелкий серый текст) к жёсткому

# Ступени размытия (GaussianBlur) в цепочке деградации. История 23.09.2026:
# сначала убрал совсем ("размытие ничего не решает, распечатка плохая" -
# после теста с blur4.5), но пользователь уточнил: убрать НАДО БЫЛО только
# то, что хуже уровня, откалиброванного на макете "Сулугуни" 22.09.2026
# (ordered+blur3 - вышло ЦЕЛИКОМ и хорошо), а не размытие целиком. Уровни
# 4/4.25/4.5/4.75/5 (добавленные позже для плотных таблиц) режут читаемость
# гораздо сильнее и НЕ восстановлены - см. AUDIT_2026-09-22.md, скан
# подтвердил "текст почти не читается" при blur5, заметно хуже при blur4.75.
# THRESHOLD_BLUR_STEPS (threshold+blur, отдельная ступень, добавленная в этой
# же сессии специально под очень плотные таблицы) остаётся пустой - она не
# входила в откалиброванное на Сулугуни поведение и НЕ восстановлена.
BLUR_STEPS = (3,)
THRESHOLD_BLUR_STEPS = ()

# Полная цепочка деградации качества под лимит PAGE_BUDGET, от лучшего к худшему:
# гладкие полутона -> паттерн Байера -> плоский чёрно-белый порог (без размытия -
# см. выше). Если и это не уместилось - см. prepare_page(): резерв "без поворота"
# для альбомных страниц, а не размытие.
_FULL_CHAIN = (
    [("floyd-steinberg", None, 0), ("floyd12", None, 0), ("smart", None, 0), ("smart2", None, 0), ("ordered8", None, 0), ("ordered", None, 0), ("screen", None, 0)]
    + [("screen", None, b) for b in BLUR_STEPS]
    + [("ordered", None, b) for b in BLUR_STEPS]
    + [("threshold", t, 0) for t in THRESHOLD_STEPS]
    + [("threshold", THRESHOLD_STEPS[-1], b) for b in THRESHOLD_BLUR_STEPS]
)


def _chain_step_name(mode: str, thr, blur: float) -> str:
    """Человекочитаемое имя шага цепочки деградации - для лога и диагностики."""
    if thr is not None and blur:
        return f"{mode}({thr},blur{blur})"
    if thr is not None:
        return f"{mode}({thr})"
    if blur:
        return f"{mode}(blur{blur})"
    return mode


# Плотность данных по высоте листа (02.10.2026). Принтер тянет бумагу с постоянной скоростью
# и не ждёт данных: обрыв зависит не от общего объёма, а от того, насколько данные плотнее
# скорости приёма на участке листа. Модель "дырявого ведра" по 5 печатям (сканы 02.10):
# принтер принимает ~97 КБ на 10 мм бумаги и держит запас ~540 КБ (это его буфер) - она
# предсказала оба обрыва (сертификат smart 120 КБ/10мм по всему листу -> обрыв на 85%,
# фото smart 139 КБ/10мм на полосе 13 см -> обрыв у нижнего края фото), а сертификат
# ordered 61 КБ/10мм, декларация 49, фото ordered 33 - целиком. Константы взяты с запасом.
DENSITY_RATE_PER_10MM = 85_000
DENSITY_BACKLOG_MAX = 450_000


def _density_backlog(lines, total_size: int) -> tuple[int, int]:
    """Наибольшее накопление данных сверх скорости приёма принтера (байт) и номер полосы
    10 мм, где оно достигнуто. Полосы сжимаются по отдельности (дают больше байт, чем
    сжатие целиком, поэтому размеры пропорционально приводятся к реальному total_size)."""
    band = max(1, round(_c2.RESOLUTION_DPI * 10 / 25.4))
    sizes = []
    for i in range(0, len(lines), band):
        part = lines[i:i + band]
        sizes.append(sum(len(p) for p in _c2.compress_page_v2(part)) if any(any(l) for l in part) else 0)
    raw_total = sum(sizes) or 1
    backlog = worst = worst_at = 0
    for n, s in enumerate(sizes):
        backlog = max(0, backlog + s * total_size / raw_total - DENSITY_RATE_PER_10MM)
        if backlog > worst:
            worst, worst_at = backlog, n
    return int(worst), worst_at


# 05.10.2026: упаковка v2 выключена по умолчанию (давала сдвиг рамок на 1 байт, см. USE_V2 в capt_print2),
# но плотные фото, не проходящие проверку плотности в v1, без неё падали бы на ordered8 (клетка).
# V2_FALLBACK: если шаг цепочки не проходит в v1, пробуем тот же шаг в v2 (с самопроверкой декодером).
V2_FALLBACK = True


def _try_v2(lines, name, logger):
    """Запасная упаковка v2 для шага цепочки; None, если не получилось или не проходит плотность."""
    try:
        full = list(lines) + [bytes(_c2.LINE_SIZE)] * max(0, _c2.LINES_BY_PAGE - len(lines))
        p2 = _c2.compress_page_v2(full)
        if _c2._v2_decode(p2) != full:
            logger(f"  {name} [v2]: проверка декодером не прошла")
            return None
        s2 = sum(len(p) for p in p2)
        if s2 > PAGE_BUDGET:
            logger(f"  {name} [v2]: {s2} байт > лимита {PAGE_BUDGET}")
            return None
        backlog, at = _density_backlog(lines, s2)
        ok = backlog <= DENSITY_BACKLOG_MAX
        logger(f"  {name} [v2, запасной]: {s2} байт, плотность: накопление {backlog // 1024} КБ на {at * 10}-{at * 10 + 10} мм"
               + ("" if ok else ", не проходит"))
        return (p2, s2) if ok else None
    except Exception as e:  # noqa: BLE001
        logger(f"  {name} [v2]: {e!r}")
        return None


def photo_fits(pdf_path: str, mode: str = "floyd-steinberg", logger=lambda *a: None):
    """Проходит ли страница в гладком режиме (по умолчанию floyd) по объёму и плотности без отката на зернистые
    режимы (05.10.2026, правка пользователя: зерна не надо). Возвращает (проходит, байт, накопление КБ).
    Упаковка как у настоящей печати: v1, при неудаче запасной v2 (V2_FALLBACK)."""
    lines = render_page_to_bitmap(pdf_path, 0, mode, logger=logger, rotate_landscape=True)
    full = list(lines) + [bytes(_c2.LINE_SIZE)] * max(0, _c2.LINES_BY_PAGE - len(lines))
    it = iter(full)
    packets = compress_page(lambda: next(it), logger)
    size = sum(len(p) for p in packets)
    if size > PAGE_BUDGET and not V2_FALLBACK:
        return False, size, None
    backlog, _at = _density_backlog(lines, size) if size <= PAGE_BUDGET else (10 ** 9, 0)
    if size <= PAGE_BUDGET and backlog <= DENSITY_BACKLOG_MAX:
        return True, size, backlog // 1024
    if V2_FALLBACK and not getattr(_c2, "USE_V2", False):
        alt = _try_v2(lines, mode, logger)
        if alt is not None:
            return True, alt[1], None
    return False, size, (backlog // 1024 if backlog < 10 ** 9 else None)


def _run_chain(pdf_path: str, page_num: int, chain, logger, rotate_landscape: bool):
    """
    Прогоняет цепочку деградации `chain` для заданной ориентации (см.
    rotate_landscape в _render_gray_canvas), останавливаясь на первом шаге,
    уместившемся в PAGE_BUDGET, либо возвращая последний шаг цепочки, даже
    если он тоже не уместился (решение "честно отказать или попробовать
    другую ориентацию" принимает prepare_page).
    Возвращает (packets, name, size, n) - n - индекс шага в chain.
    """
    for n, (mode, thr, blur) in enumerate(chain):
        lines = render_page_to_bitmap(pdf_path, page_num, mode, thr, blur, logger=logger,
                                       rotate_landscape=rotate_landscape)
        idx = {"i": 0}

        def line_source():
            i = idx["i"]
            idx["i"] += 1
            return lines[i] if i < len(lines) else bytes(_c2.LINE_SIZE)

        packets = compress_page(line_source, logger)
        size = sum(len(p) for p in packets)
        name = _chain_step_name(mode, thr, blur)
        last = n == len(chain) - 1
        fits = size <= PAGE_BUDGET
        density = ""
        if fits:
            backlog, at = _density_backlog(lines, size)
            density = f", плотность: накопление {backlog // 1024} КБ на {at * 10}-{at * 10 + 10} мм (запас {DENSITY_BACKLOG_MAX // 1024} КБ)"
            fits = backlog <= DENSITY_BACKLOG_MAX
        logger(f"  {name}: {size} байт (лимит {PAGE_BUDGET}){density}" + ("" if fits or last else ", упрощаю"))
        if not fits and not last and V2_FALLBACK and not getattr(_c2, "USE_V2", False):
            alt = _try_v2(lines, name, logger)
            if alt is not None:
                return alt[0], name + " [v2]", alt[1], n
        if fits or last:
            return packets, name, size, n
    raise RuntimeError("Пустая цепочка деградации")  # недостижимо - chain никогда не пуст


def prepare_page(pdf_path: str, page_num: int, dithering: str = DEFAULT_DITHERING, logger=print,
                 custom_paper_mm=None):
    """
    Растр + сжатие страницы с ограничением объёма данных: страница, не помещающаяся в
    память принтера, печатается обрезанной. Если сжатые данные больше PAGE_BUDGET,
    режим упрощается по _FULL_CHAIN (начиная с первого шага, где mode == dithering).

    Альбомные страницы по умолчанию печатаются с поворотом на 90°, занимая
    лист целиком (нужно физически повернуть бумагу руками, чтобы прочитать).
    Если ДАЖЕ самый жёсткий режим деградации с поворотом не помещается в
    PAGE_BUDGET - последний резерв: та же цепочка БЕЗ поворота (найдено
    23.09.2026: поворот сам по себе может раздувать объём данных на 70-215%
    в зависимости от контента - для некоторых страниц с поворотом печать
    попросту невозможна ни при какой деградации, а без поворота - вполне).
    Тогда лист печатается целиком, но не на всю площадь (содержимое вписано
    пропорционально в верхнюю часть книжного листа). Только если и это не
    помещается - честный отказ вместо тихой порчи печати (см. ниже).

    Возвращает (пакеты, описание режима, размер в байтах).
    """
    if SETTINGS["halftone"] != "auto":
        dithering = SETTINGS["halftone"]   # settings.ini имеет приоритет над режимом очереди печати
    if dithering not in DITHERING_MODES:
        raise ValueError(f"Неизвестный режим dithering: {dithering!r} (доступны: {', '.join(DITHERING_MODES)})")
    start = next(i for i, step in enumerate(_FULL_CHAIN) if step[0] == dithering)
    chain = _FULL_CHAIN[start:]

    # Автоопределение размера бумаги (28.09.2026, поправлено 29.09.2026): принтер физически
    # ВСЕГДА подаёт лист в книжной ориентации - альбомное содержимое наш код лишь разворачивает
    # на 90° перед отправкой (rotate_landscape=True ниже), сам лист от этого не меняется. Поэтому
    # геометрия бумаги берётся по (короткая сторона, длинная сторона) страницы независимо от
    # того, как расположено содержимое - альбомная A5-страница физически такой же лист 148x210мм,
    # что и книжная A5.
    _doc = pdfium.PdfDocument(pdf_path)
    _page = _doc[page_num]
    _w_pt, _h_pt = _page.get_width(), _page.get_height()
    _doc.close()
    _short_mm, _long_mm = sorted((_w_pt / 72 * 25.4, _h_pt / 72 * 25.4))
    # custom_paper_mm - свой размер из PostScript (`*CustomPageSize`, см. capt_print_redmon):
    # только по этому явному признаку размер вне списка известных считается настоящим листом
    # (иначе - например PDF-обёртка маленькой JPG - печатается вписанным в A4, как раньше).
    _c2.apply_paper_geometry(_short_mm, _long_mm, custom=custom_paper_mm is not None)

    # LBP-810 + экономия тонера (13.10.2026): работает только на A4 с родным блоком и кластерным экраном
    # (screen); на других размерах/300 dpi экономия отключается для этого листа - иначе принтер превращает
    # полутона в шум. Явный выбор halftone в settings.ini сохраняется.
    if _c2.is_810_mode() and SETTINGS["toner_saver"] == 1:
        if _c2.RESOLUTION_DPI == 600 and ((_c2._PAGEPARMS_GEOM is None and _c2.A4_TRUE_SIZE) or _c2.native810_geom()):
            if SETTINGS["halftone"] == "auto" and dithering != "screen":
                logger(f"  LBP-810 + экономия тонера: режим {dithering} -> screen (кластерные точки, как у родного драйвера)")
                dithering = "screen"
                start = next(i for i, step in enumerate(_FULL_CHAIN) if step[0] == dithering)
                chain = _FULL_CHAIN[start:]
        else:
            logger("  LBP-810: экономия тонера на LBP-810 работает при 600 dpi для A4 и известных размеров (A5, A6, A7, свой размер); для этого листа отключена")
            SETTINGS["toner_saver"] = 0

    packets, name, size, n = _run_chain(pdf_path, page_num, chain, logger, rotate_landscape=True)

    if size > PAGE_BUDGET:
        # С поворотом не поместилось вообще ни на одном шаге - последний резерв
        # перед честным отказом: та же цепочка БЕЗ поворота.
        logger("  С поворотом не поместилось даже на самом жёстком шаге - "
               "пробую без поворота как последний резерв...")
        packets2, name2, size2, n2 = _run_chain(pdf_path, page_num, chain, logger, rotate_landscape=False)
        if size2 <= PAGE_BUDGET:
            logger(f"  Без поворота уместилось: {name2} ({size2} байт) - используется как резерв "
                   "(лист использован не полностью, зато напечатан целиком)")
            return packets2, name2 + " [без поворота, резерв]", size2

    if size > PAGE_BUDGET:
        # Даже самый жёсткий режим деградации (в обеих ориентациях, если альбомная)
        # не уместился в память принтера. Раньше это молча отправлялось как есть и
        # физически обрывалось на середине листа (найдено 23.09.2026 на плотном
        # листе Excel: даже threshold(128) дал 989 КБ при лимите 520 КБ). Честный
        # отказ лучше тихой порчи печати.
        notify("Canon LBP-1120", tr(
            f"Страница слишком сложная для печати ({name}: {size // 1024} КБ, лимит {PAGE_BUDGET // 1024} КБ) - "
            "печать отменена, чтобы не обрезать лист на середине.",
            f"Page too complex to print ({name}: {size // 1024} KB, limit {PAGE_BUDGET // 1024} KB) - "
            "print cancelled to avoid cutting the sheet off mid-page."))
        raise RuntimeError(
            f"Страница не помещается в память принтера даже в самом жёстком режиме "
            f"({name}: {size} байт, лимит {PAGE_BUDGET}). Упростите содержимое страницы "
            "(уберите заливки/штриховку/частую сетку таблиц, разбейте на несколько страниц) "
                "и повторите печать.")

    return packets, name, size


def parse_args(argv):
    """Возвращает (позиционные аргументы, режим dithering)."""
    positional, dithering = [], DEFAULT_DITHERING
    i = 0
    while i < len(argv):
        if argv[i] == "--dithering" and i + 1 < len(argv):
            dithering = argv[i + 1]
            i += 2
        else:
            positional.append(argv[i])
            i += 1
    return positional, dithering


def main():
    positional, dithering = parse_args(sys.argv[1:])
    if not positional:
        print(__doc__)
        sys.exit(1)

    pdf_path = positional[0]
    page_num = int(positional[1]) - 1 if len(positional) > 1 else 0

    print(f"Рендерю страницу {page_num + 1} из {pdf_path} (dithering={dithering})...")
    packets, used, total = prepare_page(pdf_path, page_num, dithering)
    print(f"Готово: режим {used}, {len(packets)} пакет(ов), {total} байт")

    print("Отправляю на печать...")
    _c2.print_with_retry(packets, logger=print)
    print("Отправлено на печать")


if __name__ == "__main__":
    main()
