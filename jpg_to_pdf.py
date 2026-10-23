"""
Оборачивает JPG/PNG в PDF (один лист A4) БЕЗ библиотек PDF: PDF пишется напрямую,
изображение встраивается без потерь (JPEG - как есть, остальное - zlib/Flate).
Замена PyMuPDF (AGPL), 06.10.2026. Смысл прежний: обход печати изображений через
Windows GDI (Фотопросмотрщик -> Печать), которая портит светлые детали (проверено 22.09.2026).

Печатать полученный PDF через capt_print_pdf.py или через принтер "Canon LBP-1120"
как обычный PDF.

Лист: картинка кладётся на книжный A4 ровно, как есть (без поворота), вписанной в
печатаемую область листа (поля ~5 мм) и по центру. Поворот - по --rotate.
Учитывается пометка EXIF Orientation (фото с телефона/камеры).

Использование:
    python jpg_to_pdf.py фото.jpg [фото.pdf] [--rotate]
"""
import io
import sys
import zlib
from PIL import Image, ImageOps

A4_W, A4_H = 595, 842   # pt
MARGIN = 15             # pt (~5,3 мм) - не меньше непечатаемого края A4 (PPD: 13,2..15 pt)


def _pdf_page(w_px: int, h_px: int, placement, image_obj: bytes, color_space: str, image_filter: str) -> bytes:
    """Минимальный одностраничный PDF с одним изображением. placement = (x, y, dw, dh) в pt, y снизу."""
    x, y, dw, dh = placement
    content = f"q {dw:.4f} 0 0 {dh:.4f} {x:.4f} {y:.4f} cm /Im0 Do Q\n".encode("ascii")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {A4_W} {A4_H}] "
         f"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >> ").encode("ascii"),
        (f"<< /Type /XObject /Subtype /Image /Width {w_px} /Height {h_px} /ColorSpace /{color_space} "
         f"/BitsPerComponent 8 /Filter /{image_filter} /Length {len(image_obj)} >>\nstream\n").encode("ascii")
        + image_obj + b"\nendstream",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"endstream",
    ]
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("ascii")
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("ascii")
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    return bytes(out)


def wrap_image_as_pdf(image_path: str, pdf_path: str, rotate: bool = False,
                      valign: str = "top", halign: str = "center", scale: float = 1.0) -> None:
    """valign: top (по умолчанию) / center / bottom; halign: left / center / right."""
    with Image.open(image_path) as im:
        is_jpeg = im.format == "JPEG"
        reencode = im.getexif().get(274, 1) not in (1, None)   # 274 = EXIF Orientation
        oriented = ImageOps.exif_transpose(im) if reencode else im
        w, h = oriented.size
        if rotate and w > h:
            oriented = oriented.rotate(90, expand=True)
            reencode = True
            w, h = oriented.size

        if is_jpeg and not reencode and im.mode in ("L", "RGB"):
            # JPEG без изменений: встраиваем исходные байты, без перекодирования
            with open(image_path, "rb") as f:
                image_obj = f.read()
            image_filter = "DCTDecode"
            color_space = "DeviceGray" if im.mode == "L" else "DeviceRGB"
        else:
            # пиксели повёрнуты или формат иной - без потерь (Flate)
            mode = "L" if oriented.mode == "L" else "RGB"
            raw = oriented.convert(mode).tobytes()
            image_obj = zlib.compress(raw, 9)
            image_filter = "FlateDecode"
            color_space = "DeviceGray" if mode == "L" else "DeviceRGB"

    box_x0, box_y0 = MARGIN, MARGIN                      # нижний левый угол области (PDF: y снизу)
    box_w, box_h = A4_W - 2 * MARGIN, A4_H - 2 * MARGIN
    fit = min(box_w / w, box_h / h) * max(0.1, min(1.0, scale))   # scale < 1 - уменьшить фото
    dw, dh = w * fit, h * fit
    x0 = {"left": box_x0, "right": box_x0 + box_w - dw}.get(halign, box_x0 + (box_w - dw) / 2)
    # valign задан сверху вниз (top = у верхнего края области), в PDF y отсчитывается снизу
    top_gap = {"top": 0.0, "bottom": box_h - dh}.get(valign, (box_h - dh) / 2)
    y_bottom = box_y0 + box_h - top_gap - dh

    pdf = _pdf_page(w, h, (x0, y_bottom, dw, dh), image_obj, color_space, image_filter)
    with open(pdf_path, "wb") as f:
        f.write(pdf)


def main():
    args = [a for a in sys.argv[1:] if a != "--rotate"]
    if not args:
        print(__doc__)
        sys.exit(1)

    image_path = args[0]
    pdf_path = args[1] if len(args) > 1 else image_path.rsplit(".", 1)[0] + ".pdf"

    wrap_image_as_pdf(image_path, pdf_path, rotate="--rotate" in sys.argv[1:])
    print(f"PDF создан: {pdf_path}")
    print(f"Печать: python capt_print_pdf.py \"{pdf_path}\"")


if __name__ == "__main__":
    main()
