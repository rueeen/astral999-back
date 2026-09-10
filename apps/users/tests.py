from datetime import UTC, datetime, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
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

    @override_settings(TRIAL_MODE=False, TRIAL_ENDS_AT='')
    def test_register_is_unchanged_when_trial_mode_is_disabled(self):
        response = self.client.post(self.url, {
            'username': 'gratis',
            'email': 'gratis@example.com',
            'password': 'UnaClaveFuerte!999',
        })

        user = get_user_model().objects.get(username='gratis')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['plan'], 'free')
        self.assertIsNone(response.data['plan_expires_at'])
        self.assertEqual(user.plan, 'free')
        self.assertFalse(user.is_trial_grant)

    @override_settings(TRIAL_MODE=True, TRIAL_ENDS_AT='2026-10-10T23:59:59Z')
    def test_register_receives_expiring_trial_plan(self):
        response = self.client.post(self.url, {
            'username': 'prueba',
            'email': 'prueba@example.com',
            'password': 'UnaClaveFuerte!999',
        })

        user = get_user_model().objects.get(username='prueba')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['plan'], 'premium')
        self.assertEqual(
            user.plan_expires_at, datetime(2026, 10, 10, 23, 59, 59, tzinfo=UTC),
        )
        self.assertTrue(user.is_trial_grant)


class TrialPlanTests(APITestCase):
    @override_settings(TRIAL_MODE=True, TRIAL_ENDS_AT='2026-10-10T23:59:59Z')
    def test_dry_run_does_not_modify_users(self):
        user = get_user_model().objects.create_user(username='gratis')
        output = StringIO()

        call_command('grant_trial_plan', '--dry-run', stdout=output)

        user.refresh_from_db()
        self.assertEqual(user.plan, 'free')
        self.assertIn('1 cuenta(s)', output.getvalue())

    @override_settings(TRIAL_MODE=True, TRIAL_ENDS_AT='2026-10-10T23:59:59Z')
    def test_command_is_idempotent_and_preserves_later_expiration(self):
        free_user = get_user_model().objects.create_user(
            username='gratis', email='gratis@example.com',
        )
        later = datetime(2027, 1, 1, tzinfo=UTC)
        paid_user = get_user_model().objects.create_user(
            username='pago', email='pago@example.com',
            plan='premium', plan_expires_at=later,
        )

        first_output = StringIO()
        call_command('grant_trial_plan', stdout=first_output)
        second_output = StringIO()
        call_command('grant_trial_plan', stdout=second_output)

        free_user.refresh_from_db()
        paid_user.refresh_from_db()
        self.assertTrue(free_user.is_trial_grant)
        self.assertEqual(paid_user.plan_expires_at, later)
        self.assertFalse(paid_user.is_trial_grant)
        self.assertIn('1 cuenta(s)', first_output.getvalue())
        self.assertIn('0 cuenta(s)', second_output.getvalue())

    def test_expired_premium_is_not_current(self):
        user = get_user_model().objects.create_user(
            username='caducado', plan='premium',
            plan_expires_at=timezone.now() - timedelta(seconds=1),
            is_trial_grant=True,
        )
        self.assertFalse(user.is_premium)


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
