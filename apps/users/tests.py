from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


class RegisterTests(APITestCase):
    url = '/api/auth/register/'

    def test_rejects_weak_password(self):
        response = self.client.post(self.url, {
            'username': 'persona',
            'email': 'persona@example.com',
            'password': 'password',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_rejects_duplicate_email_case_insensitively(self):
        get_user_model().objects.create_user(
            username='existente', email='persona@example.com', password='UnaClaveFuerte!999'
        )

        response = self.client.post(self.url, {
            'username': 'otra',
            'email': 'PERSONA@example.com',
            'password': 'OtraClaveFuerte!999',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(str(response.data['email'][0]), 'Ya existe una cuenta con este email.')
