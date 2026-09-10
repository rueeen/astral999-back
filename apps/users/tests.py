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


class UserUpdateTests(APITestCase):
    url = '/api/users/me/'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='persona', email='persona@example.com', password='UnaClaveFuerte!999',
        )
        self.client.force_authenticate(self.user)

    def profile_data(self, email):
        return {
            'email': email, 'first_name': '', 'last_name': '', 'bio': '',
            'birth_date': None, 'birth_time': None, 'birth_place': '',
        }

    def test_normalizes_own_email_to_lowercase(self):
        response = self.client.put(
            self.url, self.profile_data('PERSONA@EXAMPLE.COM'), format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'persona@example.com')

    def test_rejects_another_users_email_case_insensitively(self):
        get_user_model().objects.create_user(
            username='otra', email='otra@example.com', password='OtraClaveFuerte!999',
        )

        response = self.client.put(
            self.url, self.profile_data('OTRA@example.com'), format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(str(response.data['email'][0]), 'Ya existe una cuenta con este email.')

    def test_new_user_uses_neutral_treatment_by_default(self):
        new_user = get_user_model().objects.create_user(username='neutral')
        self.assertEqual(new_user.address_as, 'neutral')

    def test_can_patch_treatment_without_sending_full_profile(self):
        response = self.client.patch(self.url, {'address_as': 'feminine'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.address_as, 'feminine')
