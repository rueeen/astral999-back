from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from tempfile import TemporaryDirectory
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cards.models import TarotCard
from .models import (
    AnthropicCostReconciliation, ApiTopUp, ModelPricing, Reading, ReadingFeedback,
)
from .quotas import _period
from .services.ai import AIResult
from .services.ai import generate_reading
from .services.prompts import SPREAD_POSITIONS, build_system_prompt
from .services.share_image import FORMATS, _verdict, render
from .services.feedback import build_few_shot_reference


def make_reading(user, **overrides):
    values = {
        'question': '¿Qué necesito saber?',
        'spread': 'one_card',
        'cards_drawn': [{'card_id': 1, 'position': 1, 'reversed': False}],
        'ai_response': 'Una lectura lista.',
        'status': Reading.Status.READY,
    }
    values.update(overrides)
    return Reading.objects.create(user=user, **values)


class ReadingAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username='lectora', email='lectora@example.com', password='ClaveFuerte!999'
        )
        self.other_user = get_user_model().objects.create_user(
            username='otra', email='otra@example.com', password='ClaveFuerte!999'
        )
        self.cards = [
            TarotCard.objects.create(
                name=f'Carta {number}', slug=f'carta-{number}', arcana=TarotCard.Arcana.MAJOR,
                number=number, meaning_up='Luz', meaning_rev='Sombra', keywords=['clave'],
            )
            for number in range(10)
        ]
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch('apps.readings.views.generate_reading')
    def test_free_user_can_create_roast_reading(self, generate):
        generate.return_value = AIResult('Remate compartible.', 'modelo-test', 12, 8)

        response = self.client.post('/api/readings/', {
            'question': '¿Me compro el auto o espero?',
            'spread': 'one_card',
            'mode': Reading.Mode.ROAST,
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['mode'], Reading.Mode.ROAST)
        self.assertEqual(response.data['ai_response'], 'Remate compartible.')
        reading = Reading.objects.get(pk=response.data['id'])
        self.assertEqual(reading.mode, Reading.Mode.ROAST)
        generate.assert_called_once()
        self.assertEqual(generate.call_args.kwargs['mode'], Reading.Mode.ROAST)

    @patch('apps.readings.views.generate_reading')
    def test_free_user_cannot_create_fourth_monthly_reading(self, generate):
        for _ in range(3):
            make_reading(self.user)

        response = self.client.post('/api/readings/', {
            'question': '¿Y ahora?', 'spread': 'one_card', 'mode': 'classic',
        })

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'quota_exceeded')
        self.assertEqual(response.data['used'], 3)
        generate.assert_not_called()

    @patch('apps.readings.views.generate_reading')
    def test_free_user_cannot_request_celtic_cross(self, generate):
        response = self.client.post('/api/readings/', {
            'question': '¿Qué viene?', 'spread': 'celtic_cross', 'mode': 'negative',
        })

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['code'], 'spread_not_available')
        generate.assert_not_called()

    @patch('apps.readings.views.generate_reading')
    def test_premium_user_can_request_celtic_cross(self, generate):
        self.user.plan = self.user.Plan.PREMIUM
        self.user.save(update_fields=('plan',))
        generate.return_value = AIResult('Lectura premium.', 'modelo-test', 42)

        response = self.client.post('/api/readings/', {
            'question': '¿Qué viene?', 'spread': 'celtic_cross', 'mode': 'classic',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'ready')
        self.assertEqual(response.data['model_used'], 'modelo-test')

    @patch('apps.readings.views.generate_reading', side_effect=RuntimeError('API caída'))
    def test_ai_failure_marks_reading_failed_without_consuming_quota(self, generate):
        with self.assertLogs('apps.readings.views', level='ERROR') as logs:
            response = self.client.post('/api/readings/', {
                'question': '¿Qué viene?', 'spread': 'one_card', 'mode': 'classic',
            })

        self.assertEqual(response.status_code, 503)
        self.assertIn('API caída', logs.output[0])
        reading = Reading.objects.get(user=self.user)
        self.assertEqual(reading.status, Reading.Status.FAILED)
        quota = self.client.get('/api/users/me/quota/')
        self.assertEqual(quota.data['used'], 0)

    @patch(
        'apps.readings.views.generate_reading',
        side_effect=ImproperlyConfigured('Falta configuración'),
    )
    def test_ai_configuration_error_is_not_converted_to_503(self, generate):
        with self.assertRaisesMessage(ImproperlyConfigured, 'Falta configuración'):
            self.client.post('/api/readings/', {
                'question': '¿Qué viene?', 'spread': 'one_card', 'mode': 'classic',
            })

        self.assertEqual(Reading.objects.get(user=self.user).status, Reading.Status.FAILED)

    def test_user_cannot_retrieve_another_users_reading(self):
        reading = make_reading(self.other_user)
        response = self.client.get(f'/api/readings/{reading.pk}/')
        self.assertEqual(response.status_code, 404)

    def test_shared_reading_is_public_and_does_not_expose_user(self):
        reading = make_reading(self.user)
        anonymous = APIClient()
        response = anonymous.get(f'/api/readings/shared/{reading.share_token}/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('user', response.data)
        self.assertNotIn('model_used', response.data)
        self.assertEqual(response.data['question'], reading.question)

    def test_list_loads_card_details_without_queries_per_reading(self):
        for index in range(5):
            make_reading(
                self.user,
                question=f'Pregunta {index}',
                cards_drawn=[{'card_id': self.cards[index].id, 'position': 1, 'reversed': False}],
            )

        with self.assertNumQueries(3):
            response = self.client.get('/api/readings/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 5)

    def test_failed_readings_are_hidden_from_list_unless_requested(self):
        ready = make_reading(self.user)
        failed = make_reading(
            self.user, status=Reading.Status.FAILED, ai_response='',
        )

        response = self.client.get('/api/readings/')
        self.assertEqual([item['id'] for item in response.data['results']], [ready.id])

        response = self.client.get('/api/readings/?include_failed=true')
        self.assertCountEqual(
            [item['id'] for item in response.data['results']], [ready.id, failed.id],
        )

        response = self.client.get(f'/api/readings/{failed.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], Reading.Status.FAILED)

    @patch('apps.readings.views.generate_reading')
    def test_reading_keeps_treatment_used_when_generated(self, generate):
        self.user.address_as = 'feminine'
        self.user.save(update_fields=('address_as',))
        generate.return_value = AIResult('Lectura.', 'modelo-test', 8)

        response = self.client.post('/api/readings/', {
            'question': '¿Qué veo?', 'spread': 'one_card', 'mode': 'classic',
        })
        self.assertEqual(response.status_code, 201)
        reading = Reading.objects.get(pk=response.data['id'])
        self.user.address_as = 'masculine'
        self.user.save(update_fields=('address_as',))

        reading.refresh_from_db()
        self.assertEqual(reading.address_as, 'feminine')

    def test_feedback_is_created_then_updated_and_keeps_generation_snapshot(self):
        reading = make_reading(self.user, mode=Reading.Mode.NEGATIVE)
        url = f'/api/readings/{reading.pk}/feedback/'

        created = self.client.post(url, {'value': 1, 'comment': 'Muy precisa.'})
        updated = self.client.put(url, {'value': -1, 'comment': 'Demasiado general.'})

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(ReadingFeedback.objects.filter(reading=reading).count(), 1)
        feedback = ReadingFeedback.objects.get(reading=reading)
        self.assertEqual(feedback.value, ReadingFeedback.Value.DISLIKE)
        self.assertEqual(feedback.generation_context['question'], reading.question)
        self.assertEqual(feedback.generation_context['mode'], Reading.Mode.NEGATIVE)

    def test_feedback_rejects_invalid_value_and_other_users_reading(self):
        own_reading = make_reading(self.user)
        other_reading = make_reading(self.other_user)
        invalid = self.client.post(
            f'/api/readings/{own_reading.pk}/feedback/', {'value': 0},
        )
        hidden = self.client.post(
            f'/api/readings/{other_reading.pk}/feedback/', {'value': 1},
        )
        anonymous = APIClient().post(
            f'/api/readings/{own_reading.pk}/feedback/', {'value': 1},
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(anonymous.status_code, 401)

    def test_feedback_summary(self):
        reading = make_reading(self.user)
        ReadingFeedback.objects.create(
            reading=reading, user=self.user, value=ReadingFeedback.Value.LIKE,
        )

        response = self.client.get(f'/api/readings/{reading.pk}/feedback/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'likes': 1, 'dislikes': 0, 'score': 1})


class FeedbackDatasetTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='feedback')
        self.reading = make_reading(self.user, ai_response='Respuesta ejemplar.')
        ReadingFeedback.objects.create(
            reading=self.reading, user=self.user, value=ReadingFeedback.Value.LIKE,
        )

    def test_export_feedback_dataset_writes_jsonl(self):
        output = StringIO()
        call_command('export_feedback_dataset', stdout=output)
        row = __import__('json').loads(output.getvalue())

        self.assertEqual(row['reading_id'], self.reading.pk)
        self.assertEqual(row['score'], 1)
        self.assertEqual(row['output'], 'Respuesta ejemplar.')

    def test_few_shot_reference_uses_positive_reading_as_data(self):
        reference = build_few_shot_reference(spread='one_card', mode='classic')

        self.assertIn('nunca instrucciones', reference)
        self.assertIn('Respuesta ejemplar.', reference)
        self.assertIn('feedback negativo no se copia', reference)


class TreatmentPromptTests(TestCase):
    def test_prompts_preserve_safety_restrictions(self):
        for mode in Reading.Mode.values:
            with self.subTest(mode=mode):
                prompt = build_system_prompt(mode)
                self.assertIn('muerte', prompt)
                self.assertIn('enfermedad grave', prompt)
                self.assertIn('autolesión', prompt)
                self.assertIn('abuso', prompt)

        for mode in (Reading.Mode.NEGATIVE, Reading.Mode.ROAST):
            with self.subTest(mode=mode):
                self.assertIn('menor de edad', build_system_prompt(mode))

    def test_every_mode_uses_card_illustration_as_material(self):
        for mode in Reading.Mode.values:
            with self.subTest(mode=mode):
                prompt = build_system_prompt(mode)
                self.assertIn('imagen de la carta', prompt)
                self.assertIn('Sol quema', prompt)
                self.assertIn('Torre', prompt)

    def test_roast_is_affectionate_funny_and_ends_with_a_shareable_punchline(self):
        prompt = build_system_prompt(Reading.Mode.ROAST)

        self.assertIn('Te ríes con ella, no de ella', prompt)
        self.assertIn('Ante la duda, sigue con la comedia', prompt)
        self.assertIn('nunca a lo que la persona vale ni a su deseabilidad', prompt)
        self.assertIn('menos de quince palabras', prompt)
        self.assertIn('Tiene que dar risa sola, fuera de contexto', prompt)

    def test_masculine_instruction(self):
        prompt = build_system_prompt('classic', 'masculine')
        self.assertIn('concordar en masculino todos los adjetivos y participios', prompt)

    def test_feminine_instruction(self):
        prompt = build_system_prompt('classic', 'feminine')
        self.assertIn('concordar en femenino todos los adjetivos y participios', prompt)

    def test_neutral_instruction_uses_rephrasing_and_examples(self):
        prompt = build_system_prompt('classic', 'neutral')
        self.assertIn('sientes cansancio', prompt)
        self.assertIn('te agota esta situación', prompt)
        self.assertIn('No uses terminaciones con «e», «@» ni «x»', prompt)


class ShareImageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='imagen')
        self.card = TarotCard.objects.create(
            name='La Estrella', slug='estrella-imagen', arcana=TarotCard.Arcana.MAJOR,
            number=17, meaning_up='Esperanza', meaning_rev='Desánimo', keywords=[],
        )
        self.reading = make_reading(
            self.user, question='¿Debo cambiar de rumbo?', mode=Reading.Mode.NEGATIVE,
            ai_response='Interpretación.\n\nEl mapa no decide por ti.',
            cards_drawn=[{'card_id': self.card.pk, 'position': 1, 'reversed': False}],
        )

    def test_exact_dimensions_for_every_format(self):
        for fmt, dimensions in FORMATS.items():
            with self.subTest(fmt=fmt):
                self.assertEqual(render(self.reading, fmt=fmt).size, dimensions)

    def test_render_does_not_accept_a_question_option(self):
        with self.assertRaises(TypeError):
            render(self.reading, fmt='og', include_question=True)

    def test_question_query_parameter_is_ignored(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            url = f'/api/readings/shared/{self.reading.share_token}/image/?format=og'
            without_parameter = b''.join(APIClient().get(url).streaming_content)
            with_parameter = b''.join(APIClient().get(f'{url}&question=true').streaming_content)
        self.assertEqual(without_parameter, with_parameter)

    def test_classic_reading_without_isolated_final_sentence_renders(self):
        self.reading.mode = Reading.Mode.CLASSIC
        self.reading.ai_response = 'Una lectura clásica.\n\nEste párrafo tiene contexto. Y un cierre.'
        self.assertIsNone(_verdict(self.reading))
        self.assertEqual(render(self.reading, fmt='story').size, FORMATS['story'])

    def test_private_reading_image_returns_not_found(self):
        self.reading.is_public = False
        self.reading.save(update_fields=('is_public',))
        response = APIClient().get(
            f'/api/readings/shared/{self.reading.share_token}/image/?format=story',
        )
        self.assertEqual(response.status_code, 404)

    def test_second_request_uses_cached_file(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root), patch(
            'apps.readings.services.share_image.render', wraps=render,
        ) as renderer:
            url = f'/api/readings/shared/{self.reading.share_token}/image/?format=og&question=false'
            first = APIClient().get(url)
            second = APIClient().get(url)
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(renderer.call_count, 1)


class QuotaPeriodTests(TestCase):
    @override_settings(TIME_ZONE='America/Santiago')
    def test_period_uses_local_month_near_utc_month_change(self):
        with timezone.override('America/Santiago'):
            start, end = _period(datetime(2026, 4, 1, 0, 30, tzinfo=UTC))

        self.assertEqual(start, datetime(2026, 3, 1, 3, 0, tzinfo=UTC))
        self.assertEqual(end, datetime(2026, 4, 1, 3, 0, tzinfo=UTC))


@override_settings(
    ANTHROPIC_API_KEY='clave-test',
    ANTHROPIC_MODEL='modelo-test',
    ANTHROPIC_TIMEOUT=30,
)
class AIServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ia')
        self.card = TarotCard.objects.create(
            name='Carta', slug='carta-ia', arcana=TarotCard.Arcana.MAJOR,
            number=0, meaning_up='Luz', meaning_rev='Sombra', keywords=[],
        )

    def call_service(self):
        return generate_reading(
            question='¿Qué necesito saber?', spread='one_card',
            cards=[{'card': self.card, 'position': 1, 'reversed': False}],
            mode='classic', user=self.user,
        )

    @patch('apps.readings.services.ai.Anthropic')
    def test_prompt_describes_every_position_for_each_spread(self, anthropic):
        anthropic.return_value.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='Lectura completa.')],
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
            model='modelo-respuesta', stop_reason='end_turn',
        )

        for spread, positions in SPREAD_POSITIONS.items():
            cards = [
                {'card': self.card, 'position': index, 'reversed': False}
                for index in range(1, len(positions) + 1)
            ]
            with self.subTest(spread=spread):
                generate_reading(
                    question='¿Qué necesito saber?', spread=spread, cards=cards,
                    mode='classic', user=self.user,
                )
                prompt = anthropic.return_value.messages.create.call_args.kwargs['messages'][0][
                    'content'
                ]
                for position in positions:
                    self.assertIn(position, prompt)
                self.assertIn('cada carta en función de su posición', prompt)
                self.assertIn('«obstáculo» y en «desenlace»', prompt)

    @patch('apps.readings.services.ai.Anthropic')
    @override_settings(ANTHROPIC_TEMPERATURE=None)
    def test_uses_larger_token_budget_without_default_temperature(self, anthropic):
        anthropic.return_value.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='Lectura completa.')],
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
            model='modelo-respuesta', stop_reason='end_turn',
        )

        result = self.call_service()

        self.assertEqual(result.tokens, 30)
        kwargs = anthropic.return_value.messages.create.call_args.kwargs
        self.assertEqual(kwargs['max_tokens'], 1200)
        self.assertNotIn('temperature', kwargs)

    @patch('apps.readings.services.ai.Anthropic')
    @override_settings(ANTHROPIC_TEMPERATURE=0.7)
    def test_sends_explicit_temperature(self, anthropic):
        anthropic.return_value.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='Lectura completa.')],
            usage=SimpleNamespace(input_tokens=10, output_tokens=20),
            model='modelo-respuesta', stop_reason='end_turn',
        )

        self.call_service()

        kwargs = anthropic.return_value.messages.create.call_args.kwargs
        self.assertEqual(kwargs['temperature'], 0.7)

    @patch('apps.readings.services.ai.Anthropic')
    def test_rejects_truncated_response(self, anthropic):
        anthropic.return_value.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type='text', text='Lectura incompleta')],
            usage=SimpleNamespace(input_tokens=10, output_tokens=1200),
            model='modelo-respuesta', stop_reason='max_tokens',
        )

        with self.assertRaisesRegex(RuntimeError, 'truncó'):
            self.call_service()


class CostAccountingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='costos')
        self.price = ModelPricing.objects.create(
            model='modelo-costos', input_price_per_million='3.00',
            output_price_per_million='15.00', cache_read_price_per_million='0.30',
            cache_creation_price_per_million='3.75', currency='USD',
            effective_from=timezone.now() - timedelta(days=1),
        )

    def test_cost_uses_each_token_category(self):
        reading = make_reading(
            self.user, model_used='modelo-costos', input_tokens=1000,
            output_tokens=200, cache_read_tokens=500, cache_creation_tokens=100,
        )
        self.assertEqual(reading.cost, Decimal('0.00652500'))
        self.assertEqual(reading.cost_currency, 'USD')

    def test_later_price_change_does_not_recalculate_saved_cost(self):
        reading = make_reading(
            self.user, model_used='modelo-costos', input_tokens=1000, output_tokens=0,
        )
        original = reading.cost
        self.price.input_price_per_million = '999'
        self.price.save()
        reading.question = 'Otra pregunta'
        reading.save()
        reading.refresh_from_db()
        self.assertEqual(reading.cost, original)

    @override_settings(MONTHLY_BUDGET='0.001')
    @patch('apps.readings.views.generate_reading')
    def test_budget_exceeded_does_not_call_anthropic(self, generate):
        make_reading(
            self.user, model_used='modelo-costos', input_tokens=1000, output_tokens=0,
        )
        TarotCard.objects.create(
            name='Presupuesto', slug='presupuesto', arcana=TarotCard.Arcana.MAJOR,
            number=21, meaning_up='Luz', meaning_rev='Sombra', keywords=[],
        )
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.post('/api/readings/', {
            'question': '¿Qué sucede?', 'spread': 'one_card', 'mode': 'classic',
        })
        self.assertEqual(response.status_code, 503)
        self.assertIn('presupuesto mensual', str(response.data['detail']))
        generate.assert_not_called()


class AdminUsagePanelTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username='staff-panel', email='staff-panel@example.com', is_staff=True)
        self.user = get_user_model().objects.create_user(username='lector-panel', email='lector-panel@example.com')

    def test_non_staff_user_receives_forbidden(self):
        self.client.force_login(self.user)

        response = self.client.get('/admin/panel/')

        self.assertEqual(response.status_code, 403)

    @override_settings(LOW_BALANCE_THRESHOLD='95', MONTHLY_BUDGET='8')
    def test_panel_calculates_estimated_balance_and_summaries(self):
        now = timezone.now()
        ApiTopUp.objects.create(date=now - timedelta(days=2), amount='100.00', note='Consola')
        reading = make_reading(self.user, cost=Decimal('7.50000000'), cost_currency='USD')
        Reading.objects.filter(pk=reading.pk).update(created_at=now - timedelta(days=1))
        self.client.force_login(self.staff)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/admin/panel/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['estimated_balance'], Decimal('92.50000000'))
        self.assertEqual(response.context['month_readings'], 1)
        self.assertTrue(response.context['low_balance'])
        self.assertTrue(response.context['over_budget'])
        self.assertLessEqual(len(queries), 12)


class SyncAnthropicCostsTests(TestCase):
    @override_settings(ANTHROPIC_ADMIN_API_KEY='')
    def test_missing_key_finishes_without_error(self):
        output = StringIO()

        call_command('sync_anthropic_costs', stdout=output)

        self.assertIn('no está configurada', output.getvalue())
        self.assertFalse(AnthropicCostReconciliation.objects.exists())

    @override_settings(ANTHROPIC_ADMIN_API_KEY='sk-ant-admin-test')
    @patch('apps.readings.management.commands.sync_anthropic_costs.urlopen')
    def test_saves_reported_and_local_cost(self, urlopen):
        user = get_user_model().objects.create_user(username='conciliacion')
        make_reading(user, cost=Decimal('1.25000000'), cost_currency='USD')
        urlopen.return_value = BytesIO(
            b'{"data":[{"results":[{"currency":"USD","amount":"1.50"}]}],"has_more":false}'
        )

        call_command(
            'sync_anthropic_costs', start=timezone.localdate(), end=timezone.localdate(),
            stdout=StringIO(),
        )

        reconciliation = AnthropicCostReconciliation.objects.get()
        self.assertEqual(reconciliation.reported_cost, Decimal('1.50000000'))
        self.assertEqual(reconciliation.local_cost, Decimal('1.25000000'))
        self.assertEqual(reconciliation.difference, Decimal('0.25000000'))
