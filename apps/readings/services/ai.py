from dataclasses import dataclass

from anthropic import Anthropic
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .prompts import build_system_prompt


@dataclass(frozen=True)
class AIResult:
    text: str
    model: str
    tokens: int


def generate_reading(*, question, spread, cards, mode, user):
    if not settings.ANTHROPIC_API_KEY or not settings.ANTHROPIC_MODEL:
        raise ImproperlyConfigured(
            'ANTHROPIC_API_KEY y ANTHROPIC_MODEL son obligatorias para generar lecturas.'
        )

    card_lines = []
    for drawn in cards:
        card = drawn['card']
        orientation = 'invertida' if drawn['reversed'] else 'derecha'
        meaning = card.meaning_rev if drawn['reversed'] else card.meaning_up
        card_lines.append(
            f"Posición {drawn['position']}: {card.name} ({orientation}). Significado: {meaning}"
        )
    astrology = (
        f"Signo: {user.get_zodiac_sign() or 'no informado'}; "
        f"hora de nacimiento: {user.birth_time or 'no informada'}; "
        f"lugar de nacimiento: {user.birth_place or 'no informado'}."
    )
    prompt = (
        f'Pregunta: {question}\nTirada: {spread}\nContexto astrológico: {astrology}\n'
        f"Cartas:\n" + '\n'.join(card_lines)
    )
    client = Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.ANTHROPIC_TIMEOUT,
        max_retries=1,
    )
    request_options = dict(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=1200,
        system=build_system_prompt(mode, user.address_as),
        messages=[{'role': 'user', 'content': prompt}],
    )
    # Los modelos Anthropic de generación 5 solo aceptan la temperatura predeterminada.
    # Por eso no enviamos el parámetro salvo que el entorno lo configure explícitamente.
    if settings.ANTHROPIC_TEMPERATURE is not None:
        request_options['temperature'] = settings.ANTHROPIC_TEMPERATURE
    response = client.messages.create(**request_options)
    if response.stop_reason == 'max_tokens':
        raise RuntimeError('Anthropic truncó la lectura al alcanzar el límite de tokens.')
    text = ''.join(block.text for block in response.content if block.type == 'text').strip()
    if not text:
        raise RuntimeError('Anthropic devolvió una lectura vacía.')
    tokens = response.usage.input_tokens + response.usage.output_tokens
    return AIResult(text=text, model=response.model, tokens=tokens)
