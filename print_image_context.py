"""
Обработчик правого клика "Печать через LBP1120" для JPG/PNG (регистрируется
setup.ps1 в контекстном меню Windows). Оборачивает картинку в PDF в обход
GDI-печати (см. jpg_to_pdf.py - иначе очень светлые детали теряются) и
печатает через capt_print_pdf.py. Прогресс/ошибки - всплывающим уведомлением
Windows (никакого консольного окна, запускается через pythonw.exe).
"""
import os
import sys
import tempfile
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jpg_to_pdf import wrap_image_as_pdf
from capt_print2 import notify, tr, SETTINGS_DIR, SETTINGS

import time


def _log(text: str) -> None:
    """Вывод печати картинки - в общий лог capt_redmon.log (02.10.2026: раньше терялся,
    и при ошибке в уведомлении была только обрезанная команда без причины)."""
    try:
        with open(os.path.join(SETTINGS_DIR, "capt_redmon.log"), "a", encoding="utf-8") as f:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            for line in text.splitlines():
                f.write(f"{stamp} [PID {os.getpid()}] [картинка] {line}\n")
    except OSError:
        pass

# Только на Windows: подавляет мигающее консольное окно у дочернего python.exe
# (S10) - мы запускаем не pythonw.exe, а python.exe, чтобы получить его
# stdout/stderr через capture_output, иначе окно иначе не спрятать.
CREATE_NO_WINDOW = 0x08000000


def _find_scale(image_path, rotate, valign, halign, tmp_pdf):
    """Наибольший масштаб фото (100, 95, ... 50 %), при котором печать проходит в ГЛАДКОМ режиме (floyd) без отката
    на зернистые режимы. 05.10.2026, правка пользователя: зерна не надо. None - не нашли."""
    import capt_print_pdf as cpdf
    import capt_print2 as c2
    c2.apply_paper_geometry(210, 297)
    for pct in range(100, 45, -5):
        wrap_image_as_pdf(image_path, tmp_pdf, rotate=rotate, valign=valign, halign=halign, scale=pct / 100.0)
        ok, size, backlog = cpdf.photo_fits(tmp_pdf)
        _log(f"Подбор размера: {pct}% - {'проходит' if ok else 'не проходит'} ({size} байт, накопление {backlog} КБ)")
        if ok:
            return pct / 100.0
    return None


def main():
    # --rotate: горизонтальное фото повернуть на 90° на весь лист (второй пункт меню);
    # без него картинка печатается ровно, как есть (решение 02.10.2026)
    rotate = "--rotate" in sys.argv[1:]
    args = [a for a in sys.argv[1:] if a != "--rotate"]
    if not args:
        return 1

    # Модель принтера (14.10.2026): без этого картинки по правому клику шли только на LBP-1120, а LBP-810 не находился.
    # Режим 810 включается переменной окружения; дочерний capt_print_pdf.py наследует её.
    try:
        import capt_print2 as _c2
        _model = _c2.detect_model(SETTINGS.get("image_printer", "auto"))
        if _model == "810":
            os.environ["CAPT_ENABLE_810"] = "1"
        _log(f"Принтер для картинки: {_model or 'не найден'} (image_printer={SETTINGS.get('image_printer', 'auto')})")
    except Exception as _e:  # noqa: BLE001
        _log(f"Определение модели принтера не удалось: {_e!r}")

    image_path = args[0]
    name = os.path.basename(image_path)
    here = os.path.dirname(os.path.abspath(__file__))

    # S9: PDF - во временной папке, а не рядом с картинкой. Рядом может не
    # быть прав на запись (сетевой диск, флешка с защитой от записи, папка
    # только для чтения) - печать падала бы ещё до старта capt_print_pdf.py.
    # Уникальное имя (mkstemp) также страхует от коллизии, если пользователь
    # запустит печать нескольких файлов с одинаковым именем почти одновременно.
    fd, pdf_path = tempfile.mkstemp(suffix="_print.pdf", prefix="lbp1120_")
    os.close(fd)

    try:
        valign, halign = SETTINGS.get("photo_valign", "top"), SETTINGS.get("photo_halign", "center")
        scale = 1.0
        if SETTINGS.get("photo_fit", "shrink") == "shrink":
            found = _find_scale(image_path, rotate, valign, halign, pdf_path)
            scale = found if found else 1.0
        wrap_image_as_pdf(image_path, pdf_path, rotate=rotate, valign=valign, halign=halign, scale=scale)
        _log(f"Печать картинки {image_path}" + (" (поворот на весь лист)" if rotate else ""))
        r = subprocess.run(
            [sys.executable.replace("pythonw.exe", "python.exe"),
             os.path.join(here, "capt_print_pdf.py"), pdf_path],
            capture_output=True, text=True, errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        _log((r.stdout or "") + (r.stderr or ""))
        if r.returncode != 0:
            last = [l for l in (r.stderr or r.stdout or "").splitlines() if l.strip()]
            raise RuntimeError(last[-1] if last else f"код {r.returncode}")
        extra_ru = f" (уменьшено до {int(scale * 100)}% для гладкой печати)" if scale < 1.0 else ""
        extra_en = f" (reduced to {int(scale * 100)}% for smooth print)" if scale < 1.0 else ""
        notify("Canon LBP-1120", tr(f"Отправлено на печать: {name}{extra_ru}", f"Sent to print: {name}{extra_en}"))
        return 0
    except Exception as e:
        notify("Canon LBP-1120", tr(f"Ошибка печати {name}: {e}", f"Print error for {name}: {e}"))
        return 1
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
