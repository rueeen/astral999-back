"""Renderizado reproducible de imágenes públicas para compartir lecturas."""
import base64
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
    paragraphs = [part.strip() for part in reading.ai_response.split('\n') if part.strip()]
    return paragraphs[-1] if paragraphs else 'Tu lectura ya está lista.'


def render(reading, *, fmt, include_question=True):
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
    draw.text((margin, margin), 'ASTRAL 999', font=_font(28, bold=True), fill=accent)

    y = margin + 62
    title_font = _font(44 if fmt != 'og' else 34, bold=True)
    draw.text((margin, y), 'Tu tirada', font=title_font, fill='#f5efff')
    y += title_font.size + 30

    ids = [item.get('card_id') for item in reading.cards_drawn]
    cards = {card.pk: card for card in TarotCard.objects.filter(pk__in=ids)}
    names = []
    for item in reading.cards_drawn:
        card = cards.get(item.get('card_id'))
        if card:
            names.append(f"{card.name}{' · invertida' if item.get('reversed') else ''}")
    cards_text = '  ✦  '.join(names) or 'Las cartas de tu tirada'
    y = _draw_block(
        draw, cards_text, xy=(margin, y), font=_font(25 if fmt == 'og' else 30),
        fill='#cfc3dc', width=width - margin * 2, spacing=10, max_lines=3,
    ) + 24

    if include_question and reading.question:
        draw.text((margin, y), 'LA PREGUNTA', font=_font(20, bold=True), fill=accent)
        y += 34
        y = _draw_block(
            draw, reading.question, xy=(margin, y), font=_font(27 if fmt == 'og' else 32),
            fill='#eee7f5', width=width - margin * 2, max_lines=3,
        ) + 28

    verdict = _verdict(reading)
    labels = {
        reading.Mode.CLASSIC: 'LA LECTURA',
        reading.Mode.NEGATIVE: 'EL VEREDICTO',
        reading.Mode.ROAST: 'EL REMATE',
    }
    label = labels[reading.mode]
    draw.text((margin, y), label, font=_font(21, bold=True), fill=accent)
    y += 42
    verdict_size = 48 if fmt == 'og' else (64 if fmt == 'post' else 72)
    available_height = height - y - 150
    _draw_block(
        draw, verdict, xy=(margin, y), font=_font(verdict_size, bold=True),
        fill='#ffffff', width=width - margin * 2, spacing=18,
        max_lines=max(2, available_height // (verdict_size + 18)),
    )

    watermark = 'Astral 999  ·  astral999.com'
    watermark_font = _font(21)
    bbox = draw.textbbox((0, 0), watermark, font=watermark_font)
    draw.text(
        (width - margin - (bbox[2] - bbox[0]), height - margin - 24), watermark,
        font=watermark_font, fill='#867995',
    )
    return image


def get_or_render(reading, *, fmt, include_question=True):
    """Devuelve el archivo cacheado; solo renderiza una vez cada variante."""
    if fmt not in FORMATS:
        raise ValueError('El formato debe ser story, post u og.')
    privacy = 'question' if include_question else 'private'
    directory = Path(settings.MEDIA_ROOT) / 'share-images'
    path = directory / f'{reading.share_token}-{fmt}-{privacy}.png'
    if path.exists():
        return path
    directory.mkdir(parents=True, exist_ok=True)
    image = render(reading, fmt=fmt, include_question=include_question)
    temporary = path.with_suffix('.tmp')
    image.save(temporary, format='PNG', optimize=True)
    temporary.replace(path)
    return path
