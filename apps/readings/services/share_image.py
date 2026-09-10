"""Renderizado reproducible de imágenes públicas para compartir lecturas."""
import base64
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

from apps.cards.models import TarotCard

FORMATS = {
    'story': (1080, 1920),
    'post': (1080, 1350),
    'og': (1200, 630),
}
_FONT_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'


@lru_cache(maxsize=2)
def _font_data(filename):
    """Carga una fuente embebida como texto para evitar archivos binarios en Git."""
    encoded = (_FONT_DIR / f'{filename}.base64').read_bytes()
    return base64.b64decode(encoded)


def _font(size, *, bold=False):
    filename = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    return ImageFont.truetype(BytesIO(_font_data(filename)), size)


def _lines(draw, text, font, width):
    """Divide texto según su ancho real, sin depender de fuentes del sistema."""
    words = text.split()
    lines, current = [], ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if current and draw.textlength(candidate, font=font) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_block(draw, text, *, xy, font, fill, width, spacing=12, max_lines=None):
    lines = _lines(draw, text, font, width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip('.,;:') + '…'
    x, y = xy
    line_height = font.size + spacing
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def _verdict(reading):
    """Devuelve la frase final cuando está aislada en su propio párrafo."""
    paragraphs = [part.strip() for part in reading.ai_response.split('\n') if part.strip()]
    if not paragraphs:
        return None
    candidate = paragraphs[-1]
    sentences = [part for part in re.split(r'(?<=[.!?])\s+', candidate) if part]
    return candidate if len(sentences) == 1 else None


def _closing_text(reading):
    verdict = _verdict(reading)
    if verdict:
        return verdict
    paragraphs = [part.strip() for part in reading.ai_response.split('\n') if part.strip()]
    return paragraphs[-1] if paragraphs else 'Tu lectura ya está lista.'


def _draw_centered_block(draw, text, *, center_y, font, fill, width, max_lines):
    lines = _lines(draw, text, font, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip('.,;:') + '…'
    spacing = 18
    line_height = font.size + spacing
    y = center_y - (len(lines) * line_height - spacing) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (draw._image.width - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def render(reading, *, fmt):
    """Genera un PNG con datos no identificatorios de una lectura."""
    if fmt not in FORMATS:
        raise ValueError('El formato debe ser story, post u og.')

    width, height = FORMATS[fmt]
    image = Image.new('RGB', (width, height), '#120d21')
    draw = ImageDraw.Draw(image)
    margin = 76 if fmt != 'og' else 64
    accent = '#d7b46a'
    draw.rounded_rectangle(
        (margin // 2, margin // 2, width - margin // 2, height - margin // 2),
        radius=34, outline='#493761', width=3,
    )
    safe_top = 250 if fmt == 'story' else margin
    safe_bottom = height - (250 if fmt == 'story' else margin)
    y = safe_top + 20
    title_font = _font(30 if fmt != 'og' else 24, bold=True)
    draw.text((margin, y), 'LAS CARTAS', font=title_font, fill=accent)
    y += title_font.size + 24

    ids = [item.get('card_id') for item in reading.cards_drawn]
    cards = {card.pk: card for card in TarotCard.objects.filter(pk__in=ids)}
    names = []
    for item in reading.cards_drawn:
        card = cards.get(item.get('card_id'))
        if card:
            orientation = 'invertida' if item.get('reversed') else 'derecha'
            names.append(f'{card.name} · {orientation}')
    cards_text = '   ✦   '.join(names) or 'Las cartas de tu tirada'
    y = _draw_block(
        draw, cards_text, xy=(margin, y), font=_font(25 if fmt == 'og' else 32, bold=True),
        fill='#cfc3dc', width=width - margin * 2, spacing=10, max_lines=3,
    )

    verdict = _closing_text(reading)
    labels = {
        reading.Mode.CLASSIC: 'LA LECTURA',
        reading.Mode.NEGATIVE: 'EL VEREDICTO',
        reading.Mode.ROAST: 'EL REMATE',
    }
    label = labels[reading.mode]
    verdict_size = 52 if fmt == 'og' else (
        78 if reading.mode in (reading.Mode.NEGATIVE, reading.Mode.ROAST) else 68
    )
    center_y = (y + safe_bottom) // 2
    label_font = _font(21, bold=True)
    label_bbox = draw.textbbox((0, 0), label, font=label_font)
    draw.text(
        ((width - (label_bbox[2] - label_bbox[0])) / 2, center_y - verdict_size * 2),
        label, font=label_font,
        fill=accent if reading.mode == reading.Mode.ROAST else '#a99db7',
    )
    _draw_centered_block(
        draw, verdict, center_y=center_y, font=_font(verdict_size, bold=True),
        fill='#ffffff', width=width - margin * 2,
        max_lines=3 if fmt == 'og' else 6,
    )

    watermark = 'Astral 999  ·  astral999.com'
    watermark_font = _font(21)
    bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
    draw.text(
        (width - margin - (bbox[2] - bbox[0]), safe_bottom - 24), watermark,
        font=watermark_font, fill='#867995',
    )
    return image


def get_or_render(reading, *, fmt):
    """Devuelve el archivo cacheado; solo renderiza una vez cada formato."""
    if fmt not in FORMATS:
        raise ValueError('El formato debe ser story, post u og.')
    directory = Path(settings.MEDIA_ROOT) / 'share-images'
    path = directory / f'v2-{reading.share_token}-{fmt}.png'
    if path.exists():
        return path
    directory.mkdir(parents=True, exist_ok=True)
    image = render(reading, fmt=fmt)
    temporary = path.with_suffix('.tmp')
    image.save(temporary, format='PNG', optimize=True)
    temporary.replace(path)
    return path
