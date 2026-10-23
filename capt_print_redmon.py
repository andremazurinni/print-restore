"""
Приёмный скрипт для Redmon: вызывается портом Redmon, получает
PostScript-поток на STDIN (то, что сгенерировал стандартный Windows
PostScript-драйвер при печати из Word/PDF-просмотрщика/чего угодно),
конвертирует в PDF через Ghostscript, затем печатает через
уже проверенный пайплайн capt_print_pdf.py / capt_print2.py.

Настраивается как "программа" в Redmon-порту принтера.
"""
import sys
import os
import tempfile
import time

# Redmon может запускать скрипт под другой учётной записью, у которой свой TEMP,
# поэтому основной лог лежит в общедоступном C:\ProgramData\CaptPrinter.
LOG_DIRS = [os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "CaptPrinter"),
            tempfile.gettempdir()]

# Лог подробный (диагностика протокола, ~200+ строк на задание). При обычной
# эксплуатации до мегабайта набегает за годы (см. AUDIT_2026-09-22.md, C1),
# но простая ротация ничего не стоит и снимает вопрос насовсем: при
# превышении лимита текущий файл переименовывается в .log.1 (затирая
# предыдущий) и лог начинается заново.
LOG_MAX_BYTES = 5 * 1024 * 1024


def _rotate_if_needed(path: str) -> None:
    try:
        if os.path.getsize(path) > LOG_MAX_BYTES:
            old_path = path + ".1"
            os.replace(path, old_path)
    except OSError:
        pass  # лог - best-effort, ошибка ротации не должна ронять печать


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [PID {os.getpid()}] {msg}\n"
    for d in LOG_DIRS:
        try:
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, "capt_redmon.log")
            _rotate_if_needed(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
            return
        except OSError:
            continue


log("--- процесс запущен (интерпретатор стартовал) ---")


def _log_context():
    """Контекст запуска (14.10.2026): пользователь, сеанс Windows и оконная станция. Нужен, чтобы понять, почему из Redmon
    не показываются уведомления (PermissionError 0x80070005) и увидит ли пользователь окно ручного дуплекса."""
    try:
        import ctypes
        from ctypes import wintypes
        k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
        sess = wintypes.DWORD()
        k32.ProcessIdToSessionId(os.getpid(), ctypes.byref(sess))
        ws = u32.GetProcessWindowStation()
        buf = ctypes.create_unicode_buffer(256)
        need = wintypes.DWORD()
        u32.GetUserObjectInformationW(ws, 2, buf, ctypes.sizeof(buf), ctypes.byref(need))   # UOI_NAME
        log(f"контекст: пользователь={os.environ.get('USERNAME')}, сеанс процесса={sess.value}, "
            f"сеанс консоли={k32.WTSGetActiveConsoleSessionId()}, оконная станция={buf.value!r}")
    except Exception as e:  # noqa: BLE001
        log(f"контекст не определён: {e!r}")


_log_context()

import subprocess
log("subprocess импортирован")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capt_print_pdf import prepare_page, parse_args
log("capt_print_pdf импортирован")
_, DITHERING = parse_args(sys.argv[1:])  # режим задаётся в аргументах порта Redmon: --dithering ordered
# Принтер задаётся аргументом порта Redmon: --printer СЕРИЙНЫЙ_НОМЕР (очереди "принтер 1" / "принтер 2", 05.10.2026);
# без него - printer_serial из settings.ini или первый найденный принтер.
for _i, _a in enumerate(sys.argv):
    if _a == "--printer" and _i + 1 < len(sys.argv):
        os.environ["CAPT_PRINTER_SERIAL"] = sys.argv[_i + 1].strip()
        log(f"Принтер из аргумента порта: {os.environ['CAPT_PRINTER_SERIAL']}")
# Очередь Canon LBP-810 (13.10.2026): аргумент порта --model 810 разрешает поиск принтера с USB-идентификатором 260A.
# Без аргумента печать идёт только на LBP-1120, как раньше.
for _i, _a in enumerate(sys.argv):
    if _a == "--model" and _i + 1 < len(sys.argv) and sys.argv[_i + 1].strip() == "810":
        os.environ["CAPT_ENABLE_810"] = "1"
        log("Включена поддержка LBP-810 (аргумент порта --model 810)")
def _hide_own_console():
    # exe собран как консольный (Redmon передаёт PostScript через stdin), и на ряде ПК
    # Windows показывает его чёрное окно на всё время печати, несмотря на ShowWindow=0 порта.
    # Прячем окно, но только если консоль принадлежит нам (exe + его PyInstaller-родитель);
    # если запущено из чужого cmd/PowerShell, чужое окно не трогаем.
    if not getattr(sys, "frozen", False) or os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        hwnd = k32.GetConsoleWindow()
        if not hwnd:
            return
        pids = (ctypes.c_uint * 8)()
        if k32.GetConsoleProcessList(pids, 8) <= 2:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass  # косметика, печать не ломаем


_hide_own_console()

# Быстрый набор очереди (13.10.2026): аргумент порта --preset text|photo|saver|draft
for _i, _a in enumerate(sys.argv):
    if _a == "--preset" and _i + 1 < len(sys.argv):
        os.environ["CAPT_PRESET"] = sys.argv[_i + 1].strip().lower()
        log(f"Быстрый набор очереди: {os.environ['CAPT_PRESET']}")
from capt_print2 import Printer, DeviceLock, SETTINGS, SETTINGS_PATH, apply_resolution, apply_preset
log("capt_print2 импортирован (usb/libusb загружены)")

if "--counter-reset" in sys.argv:
    # Кнопка "Картридж заменён" в уведомлении о ресурсе (протокол captcounter://reset, см. setup.ps1).
    # captcounter://reset810 - счётчик LBP-810 (counter_810.json), иначе LBP-1120 (counter.json).
    try:
        import capt_counter
        from capt_print2 import notify, tr
        _is810 = any("reset810" in a for a in sys.argv)
        capt_counter.reset_cartridge(os.path.join(capt_counter.DATA_DIR, "counter_810.json") if _is810 else None)
        log("Счётчик картриджа обнулён кнопкой уведомления" + (" (LBP-810)" if _is810 else ""))
        notify("Canon LBP-810" if _is810 else "Canon LBP-1120", tr("Счётчик картриджа обнулён. Новый отсчёт начат.",
                                    "Cartridge counter reset. A new count has started."))
    except Exception as e:
        log(f"Сброс счётчика по кнопке не удался: {e}")
    sys.exit(0)

if "--install-test" in sys.argv:
    # Пробная страница в конце установки (08.10.2026, план п.7): печатает install_test_page.pdf
    # со штампом "Sr. No. <серийник>" в заголовке - вызывается setup.ps1 напрямую через exe,
    # не через Redmon-порт. Без QR и без diag_stamp (та же причина, что и всегда - в Portable/exe
    # диагностика не кладём, см. память feedback_no_diagnostic_tools_in_installer.md).
    import usb.util
    from capt_print2 import DeviceLock, print_with_retry, notify, tr
    from capt_print_pdf import set_install_stamp_serial
    try:
        with DeviceLock():
            printer = Printer(logger=log)
            serial = str(printer.dev.serial_number)
            from capt_print2 import PRODUCT_ID_810
            _is810 = printer.dev.idProduct == PRODUCT_ID_810   # 810 только при --model 810 (find_printer)
            usb.util.dispose_resources(printer.dev)
        _model = "LBP-810" if _is810 else "LBP-1120"
        from capt_print2 import _lang
        _base_dir = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
        _page = "install_test_page_810" if _is810 else "install_test_page"
        pdf_path = os.path.join(_base_dir, _page + ("" if _lang() == "ru" else "_en") + ".pdf")
        if not os.path.exists(pdf_path):   # нет листа на нужном языке - берём русский (старые пакеты)
            pdf_path = os.path.join(_base_dir, _page + ".pdf")
        log(f"install-test: принтер найден ({_model}), серийный номер {serial}")
        set_install_stamp_serial(serial, _model)
        try:
            packets, used, size = prepare_page(pdf_path, 0, DITHERING, logger=log)
        finally:
            set_install_stamp_serial(None)
        log(f"install-test: страница подготовлена ({used}, {size} байт), печатаю...")
        print_with_retry(packets, logger=log)
        log("install-test: отправлено на печать")
        sys.exit(0)
    except Exception as e:
        log(f"install-test: ОШИБКА: {e}")
        import traceback
        log(traceback.format_exc())
        try:
            notify("Canon LBP-1120", tr(f"Пробная печать не удалась: {e}",
                                        f"Test print failed: {e}"))
        except Exception:
            pass
        sys.exit(1)

def find_gs():
    """Самый свежий установленный Ghostscript, любой версии."""
    import glob
    found = []
    for pf in (os.environ.get("ProgramFiles", r"C:\Program Files"), r"C:\Program Files"):
        found += glob.glob(os.path.join(pf, "gs", "gs*", "bin", "gswin64c.exe"))
    if not found:
        raise FileNotFoundError(r"Ghostscript не найден в C:\Program Files\gs\gs*\bin")
    def version_key(path):
        name = os.path.basename(os.path.dirname(os.path.dirname(path)))[2:]
        return tuple(int(x) for x in name.split(".") if x.isdigit())
    return max(found, key=version_key)




def find_copies(ps_data: bytes) -> int:
    """
    Число копий из PostScript-задания (Excel/Word "Копии: N"): /NumCopies N в
    setpagedevice, /#copies N def (PostScript Level 1) или %%Requirements: numcopies(N).
    Ghostscript pdfwrite копии игнорирует - раньше печаталась всегда одна.
    Все найденные упоминания "copies" пишутся в лог для диагностики.
    """
    import re
    head = ps_data if len(ps_data) <= 220000 else ps_data[:200000] + ps_data[-20000:]
    for m in list(re.finditer(rb"[^\r\n]{0,80}copies[^\r\n]{0,80}", head, re.I))[:8]:
        log(f"  copies-строка: {m.group(0).decode('latin-1')!r}")
    # Шаблоны по убыванию надёжности; берём первый сработавший. Windows-драйвер пишет
    # "%%BeginNonPPDFeature: NumCopies 2"; строка "/NumCopies 4 -1 roll put" - это
    # служебная процедура PostScript (число там не копии) - раньше её путали с копиями
    # и вместо 2 печаталось 4 (проверено 24.09.2026).
    for pat in (rb"%%BeginNonPPDFeature:\s*NumCopies\s+(\d+)",
                rb"/NumCopies\s+(\d+)\s*>>",
                rb"/#copies\s+(\d+)\s+def",
                rb"numcopies\((\d+)\)"):
        found = [int(x) for x in re.findall(pat, head, re.I)]
        if found:
            return max(1, min(found[-1], 99))
    return 1


# Яркость/контраст в окне печати: Zero, Plus10..Plus100, Minus10..Minus100 (шаг 10%);
# Plus25/Minus25 оставлены для совместимости с первой версией PPD (шаг 25%).
_PERCENT_STEPS = {"Zero": 0}
for _n in list(range(10, 101, 10)) + [25]:
    _PERCENT_STEPS[f"Plus{_n}"] = _n
    _PERCENT_STEPS[f"Minus{_n}"] = -_n

_FEATURE_MAP = {
    # "Режим настроек" (30.09.2026): Standard - опции окна печати игнорируются (берётся settings.ini),
    # Manual - действуют опции окна. Нет опции (старый PPD) = Manual, как раньше.
    "CaptMode": ("settings_mode", {"Standard": "standard", "Manual": "manual"}),
    # "Счётчик картриджа": Replaced - обнулить счётчик листов (один раз), Keep - ничего не менять
    "CaptCartridge": ("cartridge", {"Keep": "keep", "Replaced": "replaced"}),
    # "Быстрый набор" (14.10.2026): работает и в режиме Standard (набор важнее остальных опций)
    "CaptPreset": ("preset", {"None": "", "Text": "text", "Photo": "photo", "Saver": "saver", "Draft": "draft"}),
    # "Manual duplex" (14.10.2026): On включает ручной дуплекс в обоих режимах; Off ничего не меняет (settings.ini остаётся в силе)
    "CaptDuplex": ("manual_duplex", {"Off": 0, "On": 1}),
    # ключ PPD (ppd_driver\LBP1120.PPD) -> (ключ настроек, {значение PPD: значение настройки})
    "Resolution": ("resolution", {"600dpi": 600, "300dpi": 300}),
    "CaptHalftone": ("halftone", {"Auto": "auto", "Pattern1": "screen", "Ordered": "ordered",
                                  "Smooth": "floyd-steinberg", "None": "threshold"}),
    "CaptDensity": ("toner_density", {"Lightest": 0, "Light": 15, "Normal": 31, "Dark": 47, "Darkest": 63}),
    "CaptTonerSaver": ("toner_saver", {"False": 0, "True": 1}),
    "CaptRefinement": ("refinement", {"False": 0, "True": 1}),
    "CaptBrightness": ("brightness", _PERCENT_STEPS),
    "CaptContrast": ("contrast", _PERCENT_STEPS),
}


def parse_job_options(ps_data: bytes) -> dict:
    """
    Опции качества из PostScript-задания: драйвер "Canon LBP-1120 (CAPT)" (PPD с
    дополнительными функциями) пишет их строками "%%BeginFeature: *CaptDensity Dark".
    Все такие строки пишутся в лог для диагностики. Возвращает словарь настроек
    (те же ключи, что в settings.ini); заданные здесь опции важнее settings.ini.
    """
    import re
    head = ps_data if len(ps_data) <= 400000 else ps_data[:300000] + ps_data[-100000:]
    found = re.findall(rb"%%BeginFeature:\s*\*(\w+)\s+([^\r\n]+)", head)
    for name, value in found[:30]:
        log(f"  feature: *{name.decode('latin-1')} {value.decode('latin-1').strip()}")
    opts = {}
    for name, value in found:
        key = name.decode("latin-1")
        if key in _FEATURE_MAP:
            skey, table = _FEATURE_MAP[key]
            val = table.get(value.decode("latin-1").strip())
            if val is not None:
                opts[skey] = val
    return opts


def detect_custom_page(ps_data: bytes):
    """
    Свой размер бумаги (30.09.2026): драйвер Windows пишет `%%BeginFeature: *CustomPageSize`
    (числа в порядке "ширина высота ..." по PPD, длинная сторона идёт как "ширина"), а настоящую
    страницу объявляет в `%%PageBoundingBox: 0 0 W H` (книжная 283x425 для 100x150 мм).
    Возвращает (W, H) в пунктах из PageBoundingBox либо None, если размер не свой.
    Ghostscript по setpageparams делает страницу альбомной с повёрнутым содержимым, поэтому
    ниже размер фиксируется по PageBoundingBox (см. main).
    """
    import re
    head = ps_data[:300000]
    if not re.search(rb"%%BeginFeature:\s*\*CustomPageSize", head):
        return None
    m = re.search(rb"%%PageBoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", head)
    if not m:
        return None
    w, h = int(m.group(3)) - int(m.group(1)), int(m.group(4)) - int(m.group(2))
    return (w, h) if w > 0 and h > 0 else None


def _read_stdin_bytes():
    # exe собран без консоли (чёрное окно при печати): у такого процесса sys.stdin = None,
    # но Redmon всё равно передаёт PostScript через унаследованный дескриптор stdin - читаем его напрямую.
    if sys.stdin is not None:
        return sys.stdin.buffer.read()
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    k32.GetStdHandle.restype = wintypes.HANDLE
    k32.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    handle = k32.GetStdHandle(-10)  # STD_INPUT_HANDLE
    if handle in (None, 0, -1, ctypes.c_void_p(-1).value):
        raise RuntimeError("stdin недоступен (нет стандартного дескриптора ввода)")
    chunks, buf, read = [], ctypes.create_string_buffer(1 << 20), wintypes.DWORD(0)
    while k32.ReadFile(handle, buf, len(buf), ctypes.byref(read), None) and read.value:
        chunks.append(buf.raw[:read.value])
    return b"".join(chunks)


def main():
    log("=== Redmon вызов начат, читаю stdin... ===")
    ps_data = _read_stdin_bytes()
    log(f"Получено {len(ps_data)} байт PostScript со stdin")
    copies = find_copies(ps_data)
    log(f"Копий: {copies}")
    job_opts = parse_job_options(ps_data)
    cart = job_opts.pop('cartridge', None)
    if cart:
        try:
            import capt_counter
            if capt_counter.option_reset(cart):
                log("Счётчик картриджа обнулён опцией окна печати")
                from capt_print2 import notify, tr
                notify("Canon LBP-1120", tr(
                    "Счётчик картриджа обнулён. Верните в настройках печати «Счётчик картриджа» на «Не менять».",
                    "Cartridge counter reset. Set \"Cartridge counter\" back to \"Keep\" in the print settings."))
        except Exception as e:
            log(f"Опция счётчика картриджа: {e}")
    win_preset = job_opts.pop('preset', None)      # быстрый набор из окна печати: действует в обоих режимах
    win_duplex = job_opts.pop('manual_duplex', None)   # ручной дуплекс из окна печати: On действует в обоих режимах
    if job_opts.pop('settings_mode', None) == 'standard':
        log("Режим настроек: Стандартный - опции окна печати игнорируются, действуют settings.ini/умолчания")
        job_opts = {}
    if job_opts.get('halftone') == 'auto' and SETTINGS.get('halftone') != 'auto':
        job_opts.pop('halftone')               # 'Auto' в очереди не затирает явный выбор в settings.ini
    for k in ('brightness', 'contrast'):   # нулевое значение из очереди не затирает ненулевое из settings.ini
        if job_opts.get(k) == 0 and SETTINGS.get(k):
            job_opts.pop(k)
    if job_opts:
        SETTINGS.update(job_opts)              # опции из окна печати важнее settings.ini
    if win_duplex == 1:
        SETTINGS["manual_duplex"] = 1
        job_opts["manual_duplex"] = 1
    preset = os.environ.get("CAPT_PRESET") or win_preset or SETTINGS.get("preset")
    if apply_preset(SETTINGS, preset, logger=log):   # быстрый набор важнее всего остального
        job_opts["preset"] = preset
    if job_opts:
        apply_resolution(SETTINGS["resolution"])
    log(f"Настройки ({SETTINGS_PATH}) + опции задания {job_opts}: {SETTINGS}")

    # Удаляем UTF-8 BOM если он есть (PowerShell Out-File его иногда добавляет)
    if ps_data.startswith(b'\xef\xbb\xbf'):
        log("Удаляю UTF-8 BOM из данных")
        ps_data = ps_data[3:]

    with tempfile.NamedTemporaryFile(suffix=".ps", delete=False) as f_ps:
        f_ps.write(ps_data)
        ps_path = f_ps.name

    pdf_path = ps_path.replace(".ps", ".pdf")

    custom_pt = detect_custom_page(ps_data)
    custom_mm = None
    gs_extra, gs_input = [], [ps_path]
    if custom_pt:
        custom_mm = (custom_pt[0] / 72 * 25.4, custom_pt[1] / 72 * 25.4)
        log(f"Свой размер бумаги: {custom_pt[0]}x{custom_pt[1]} pt = {custom_mm[0]:.1f}x{custom_mm[1]:.1f} мм")
        # страницу фиксируем по PageBoundingBox, setpageparams (делает страницу альбомной с повёрнутым
        # содержимым) превращаем в пустую операцию
        gs_extra = [f"-dDEVICEWIDTHPOINTS={custom_pt[0]}", f"-dDEVICEHEIGHTPOINTS={custom_pt[1]}", "-dFIXEDMEDIA"]
        gs_input = ["-c", "statusdict begin /setpageparams {pop pop pop pop} def end", "-f", ps_path]

    try:
        gs_exe = find_gs()
        log(f"Ghostscript: {gs_exe}")
        result = subprocess.run(
            [gs_exe, "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dBATCH", "-dSAFER",
             # 30.09.2026: драйвер Windows задаёт передаточные функции (таблицы яркости картинок);
             # по умолчанию Ghostscript оставляет их в PDF как /TR, а MuPDF (fitz) их ИГНОРИРУЕТ -
             # картинки из Word/GDI+ (в т.ч. серые фото) выходили чёрными и со сдвинутыми полосами.
             # /Apply запекает функции в данные картинки: страница выглядит так же, как в Ghostscript.
             "-dTransferFunctionInfo=/Apply", *gs_extra,
             f"-sOutputFile={pdf_path}", *gs_input],
            capture_output=True, text=True, timeout=120,
        )
        log(f"Ghostscript exit={result.returncode}")
        if result.returncode != 0:
            log(f"Ghostscript stderr: {result.stderr}")
            return 1

        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf_path)
        log(f"PDF создан, страниц: {len(doc)}")

        # Растр и сжатие считаем ДО захвата принтера: пока предыдущее задание ещё
        # печатается, следующее уже готово и данные уходят сразу, как только принтер
        # освободится (иначе принтер простаивал 2-3 с на рендеринг между заданиями).
        total_pages = len(doc)
        cache = {}
        page_list = list(range(total_pages))
        if SETTINGS.get("skip_blank_pages"):
            from capt_print_pdf import is_blank_page
            page_list = [n for n in page_list if not is_blank_page(pdf_path, n)]
            skipped = total_pages - len(page_list)
            if skipped:
                log(f"Пропуск пустых страниц: {skipped} из {total_pages} не печатаются")
            if not page_list:
                from capt_print2 import notify, tr
                log("Все страницы пустые - печать не выполнена")
                notify("Canon LBP-810" if os.environ.get("CAPT_ENABLE_810") == "1" else "Canon LBP-1120", tr(
                    "Все страницы документа пустые, печать пропущена.",
                    "All pages of the document are blank, printing skipped."))
                return 0
        # Ручной дуплекс (13.10.2026): проход 1 - нечётные страницы, проход 2 - чётные (см. capt_print_pdf.plan_manual_duplex)
        duplex = bool(SETTINGS.get("manual_duplex")) and len(page_list) > 1
        rot_back = bool(SETTINGS.get("duplex_even_rotate"))
        pad = 0
        if duplex:
            from capt_print_pdf import plan_manual_duplex, make_blank_pdf
            odd, even, pad = plan_manual_duplex(page_list, bool(SETTINGS.get("duplex_even_reverse", 1)))
            passes = [(odd, False), (even, True)]
            log(f"Ручной дуплекс: проход 1 - страницы {[n + 1 for n in odd]}, проход 2 - {[n + 1 for n in even]}"
                f"{', перед ними 1 пустой оборот' if pad else ''}{', повёрнуты на 180' if rot_back else ''}")
        else:
            passes = [(page_list, False)]
        for pages, back in passes:
            for page_num in pages:
                log(f"Готовлю страницу {page_num + 1}/{total_pages} (dithering={DITHERING})")
                saved_rot = SETTINGS.get("rotate180", 0)
                if back and rot_back:
                    SETTINGS["rotate180"] = 0 if saved_rot else 1
                try:
                    cache[(page_num, back)] = prepare_page(pdf_path, page_num, DITHERING, logger=lambda m: log(m.strip()),
                                                           custom_paper_mm=custom_mm)
                finally:
                    SETTINGS["rotate180"] = saved_rot
                log(f"Страница {page_num + 1}: режим {cache[(page_num, back)][1]}, данные {cache[(page_num, back)][2]} байт")
        if pad:
            blank_pdf = make_blank_pdf(pdf_path, pdf_path.replace(".pdf", "_blank.pdf"))
            cache[("blank", True)] = prepare_page(blank_pdf, 0, DITHERING, logger=lambda m: log(m.strip()),
                                                  custom_paper_mm=custom_mm)
            try:
                os.remove(blank_pdf)
            except OSError:
                pass

        def ask_flip():
            """Окно ручного дуплекса: True - продолжить, False - отмена. Между проходами принтер не занят."""
            from capt_print2 import notify, tr
            text = tr("Первые стороны напечатаны.\n\nВозьмите стопку из выходного лотка, не меняя порядок листов. "
                      "Переверните её, как страницу книги: верх листов остаётся сверху (на 180 градусов не разворачивать), "
                      "чистая сторона к вам, напечатанная от вас. Положите стопку в лоток подачи.\n\n"
                      "Нажмите ОК, когда стопка в лотке, или Отмена, чтобы прекратить печать.",
                      "The first sides are printed.\n\nTake the stack from the output tray without changing the sheet order. "
                      "Turn it over like a book page: the top of the sheets stays on top (do not rotate by 180 degrees), "
                      "blank side towards you, printed side away from you. Put the stack into the input tray.\n\n"
                      "Press OK when the stack is in the tray, or Cancel to stop printing.")
            from capt_print2 import user_dialog_ok_cancel
            ans = user_dialog_ok_cancel("Canon LBP", text)
            res = 0 if ans is None else (1 if ans else 2)
            if res == 0:
                notify("Canon LBP", tr("Переверните стопку и положите в лоток. Печать оборота начнётся через 90 секунд.",
                                       "Flip the stack and put it in the tray. Back sides will start printing in 90 seconds."))
                time.sleep(90)
                return True
            return res == 1

        jobs = []   # (номера копий, [(страница, оборот)], нужно ли окно переворота перед проходом)
        if duplex:
            for copy_num in range(copies):
                jobs.append(([copy_num], [(n, False) for n in passes[0][0]], False))
                back_items = ([("blank", True)] if pad else []) + [(n, True) for n in passes[1][0]]
                jobs.append(([copy_num], back_items, True))
        else:
            jobs.append((list(range(copies)), [(n, False) for n in page_list], False))

        for job_idx, (copy_nums, items, flip_before) in enumerate(jobs):
            if flip_before and not ask_flip():
                log("Ручной дуплекс: пользователь отменил печать оборотов")
                return 0
            log("Жду доступа к устройству (DeviceLock)...")
            with DeviceLock():
                log("Устройство занято этим заданием")
                printer = Printer(logger=lambda m: log(m))  # один на проход, если нет сбоев подачи
                first_on_connection = True  # первая страница, отправленная через ТЕКУЩЕЕ подключение к принтеру
                for copy_num in copy_nums:
                    for key in items:
                        page_num, back = key
                        last_in_pass = (copy_num == copy_nums[-1]) and (key == items[-1])
                        label = "пустой" if page_num == "blank" else page_num + 1
                        log(f"Печатаю страницу {label}/{total_pages}, копия {copy_num + 1}/{copies}{', оборот' if back else ''}")
                        packets, used, size = cache[key]
                        try:
                            printer.print_page(packets, first_page=first_on_connection, wait_done=last_in_pass)
                            first_on_connection = False
                        except (RuntimeError, TimeoutError) as e:
                            # 07.10.2026: сбой подачи (лист задели при захвате) - см. память
                            # lbp1120_printer_status_bits.md. У протокола нет "продолжить с
                            # прерванного места": переподключаемся и отправляем ЭТУ страницу
                            # заново как первую для НОВОГО подключения, остальной документ
                            # печатаем дальше тем же подключением. Одна повторная попытка -
                            # если снова не выйдет, честно падаем (см. except ниже, Exception as e).
                            log(f"  Сбой подачи на странице {label}, копия {copy_num + 1}: {e}")
                            import usb.util
                            try:
                                usb.util.dispose_resources(printer.dev)
                            except Exception:  # noqa: BLE001 - лишь бы не сорвать повтор
                                pass
                            from capt_print2 import notify, tr
                            notify("Canon LBP-1120", tr(
                                "Сбой при печати, переподключаюсь и повторяю эту страницу...",
                                "Printing failed, reconnecting and retrying this page..."))
                            time.sleep(2.0)
                            printer = Printer(logger=lambda m: log(m))
                            printer.print_page(packets, first_page=True, wait_done=last_in_pass)
                            first_on_connection = False
                        log(f"Страница {label}, копия {copy_num + 1} отправлена")
                # 14.10.2026: в ручном дуплексе второй проход открывает принтер заново в ТОМ ЖЕ процессе - прежний дескриптор
                # надо освободить, иначе find_printer не читает серийный номер ("The device has no langid")
                try:
                    import usb.util
                    usb.util.dispose_resources(printer.dev)
                except Exception as e:  # noqa: BLE001
                    log(f"Освобождение USB-устройства: {e!r}")

        log("=== Готово ===")
        return 0

    except Exception as e:
        log(f"ОШИБКА: {e}")
        import traceback
        log(traceback.format_exc())
        # 08.10.2026: раньше уведомление показывалось только при "не найден" (принтер
        # отключён ДО начала печати). Если USB-кабель выдёргивали ПОСЕРЕДИНЕ передачи
        # данных, pyusb кидает usb.core.USBError - этот текст "не найден" не содержит,
        # и пользователь не получал тост, только запись в журнал (см. план, п.4).
        # Теперь уведомляем при любом сбое печати, текст зависит от причины.
        try:
            import usb.core
            from capt_print2 import notify, tr
            if "не найден" in str(e):
                notify("Canon LBP-1120", tr(f"Печать не выполнена: {e}. Проверьте, что принтер включён и подключён.",
                                            f"Print failed: {e}. Check that the printer is on and connected."))
            elif isinstance(e, usb.core.USBError):
                notify("Canon LBP-1120", tr(
                    "Печать прервана: принтер пропал из USB во время печати. "
                    "Проверьте кабель и питание, затем распечатайте заново.",
                    "Printing interrupted: the printer disappeared from USB during printing. "
                    "Check the cable and power, then print again."))
            else:
                notify("Canon LBP-1120", tr(f"Печать не выполнена: {e}. Подробности в журнале.",
                                            f"Print failed: {e}. See the log for details."))
        except Exception:
            pass
        return 1  # ненулевой код: задание в очереди получит статус ошибки, а не "успех"
    finally:
        for path in (ps_path, pdf_path):
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
