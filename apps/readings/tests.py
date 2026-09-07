from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cards.models import TarotCard
from .models import Reading
from .services.ai import AIResult


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
        response = self.client.post('/api/readings/', {
            'question': '¿Qué viene?', 'spread': 'one_card', 'mode': 'classic',
        })

        self.assertEqual(response.status_code, 503)
        reading = Reading.objects.get(user=self.user)
        self.assertEqual(reading.status, Reading.Status.FAILED)
        quota = self.client.get('/api/users/me/quota/')
        self.assertEqual(quota.data['used'], 0)

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
