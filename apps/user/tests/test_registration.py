from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import Mock, patch

from ..models import SocialAccount, SocialLinkIntent, User, VerificationToken


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class UserRegistrationApiTests(APITestCase):
	def test_register_with_email_only(self):
		if hasattr(mail, "outbox"):
			del mail.outbox[:]

		response = self.client.post(
			reverse("users-list"),
			{
				"username": "alice",
				"email": "alice@example.com",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(User.objects.count(), 1)
		self.assertEqual(User.objects.first().email, "alice@example.com")
		self.assertEqual(len(getattr(mail, "outbox", [])), 1)
		self.assertEqual(mail.outbox[0].to, ["alice@example.com"])
		self.assertEqual(mail.outbox[0].subject, "Welcome to Studyzone - Verify Your Email")
		self.assertEqual(
			VerificationToken.objects.filter(user=User.objects.first(), channel="email").count(),
			1,
		)
	
	def test_register_with_phone_only(self):
		response = self.client.post(
			reverse("users-list"),
			{
				"username": "bob",
				"phone_number": "+15555555555",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
				"verification_options": "phone",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(User.objects.count(),1)
		self.assertEqual(User.objects.first().phone,'+15555555555')
		token = VerificationToken.objects.filter(user__username="bob", channel="phone").first()
		verify_response = self.client.post(
			reverse("users-verify-phone"),
			{"token": getattr(token, "_raw_token", None) or ""},
		)
		if verify_response.status_code == status.HTTP_400_BAD_REQUEST:
			# fallback: extract token from outbox body if serializer didn't expose it
			body = mail.outbox[-1].body
			raw_token = body.split("token=")[-1].strip()
			verify_response = self.client.post(
				reverse("users-verify-phone"),
				{"token": raw_token},
			)
		self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
		user = User.objects.get(username="bob")
		self.assertTrue(user.is_phone_verified)

	def test_verify_email_success(self):
		response = self.client.post(
			reverse("users-list"),
			{
				"username": "eve",
				"email": "eve@example.com",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
			},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)

		token = VerificationToken.objects.get(user__username="eve", channel="email")
		verify_response = self.client.post(
			reverse("users-verify-email"),
			{"token": getattr(token, "_raw_token", None) or ""},
			format="json",
		)

		# fallback: extract token from outbox body if serializer didn't expose it
		if verify_response.status_code == status.HTTP_400_BAD_REQUEST:
			body = mail.outbox[-1].body
			raw_token = body.split("token=")[-1].strip()
			verify_response = self.client.post(
				reverse("users-verify-email"),
				{"token": raw_token},
				format="json",
			)

		self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
		user = User.objects.get(username="eve")
		self.assertTrue(user.is_email_verified)

	def test_verify_email_rejects_invalid_token(self):
		response = self.client.post(
			reverse("users-verify-email"),
			{"token": "invalid-token"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_resend_email_verification_is_generic(self):
		response = self.client.post(
			reverse("users-resend-email-verification"),
			{"email": "missing@example.com"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("detail", response.data)

	def test_register_with_phone_only(self):
		if hasattr(mail, "outbox"):
			del mail.outbox[:]
		response = self.client.post(
			reverse("users-list"),
			{
				"username": "bob",
				"phone_number": "+15551234567",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
				"verification_options": "phone",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(User.objects.count(), 1)
		self.assertEqual(User.objects.first().phone_number, "+15551234567")
		self.assertEqual(len(getattr(mail, "outbox", [])), 0)

	def test_register_rejects_duplicate_email(self):
		User.objects.create_user(username="existing", email="alice@example.com", password="StrongPass123!")

		response = self.client.post(
			reverse("users-list"),
			{
				"username": "alice-two",
				"email": "alice@example.com",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("email", response.data)

	def test_register_requires_email_or_phone(self):
		response = self.client.post(
			reverse("users-list"),
			{
				"username": "charlie",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
			},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(User.objects.count(), 0)

	def test_register_rejects_invalid_phone_format(self):
		response = self.client.post(
			reverse("users-list"),
			{
				"username": "dora",
				"phone_number": "5551234567",
				"password": "StrongPass123!",
				"password_confirm": "StrongPass123!",
				"verification_options": "phone",
			},
			format="json",
		)
  
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("phone_number", response.data)


class UserSerializerTests(APITestCase):
	def test_user_serializer_handles_missing_profile(self):
		user = User.objects.create_user(username="profileless", password="StrongPass123!")

		self.client.force_authenticate(user=user)
		response = self.client.get(reverse("users-list"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIsNone(response.data["profile"])


@override_settings(
	EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
	SOCIAL_AUTH_ENABLED=True,
	GOOGLE_CLIENT_ID="test-google-client-id",
	SOCIAL_LINK_RESEND_COOLDOWN_SECONDS=300,
	FACEBOOK_APP_ID="test-fb-app-id",
	FACEBOOK_APP_SECRET="test-fb-app-secret",
)
class SocialAuthApiTests(APITestCase):
	@patch("apps.user.utils.google_id_token.verify_oauth2_token")
	def test_google_auth_creates_user_and_returns_jwt(self, mock_verify):
		mock_verify.return_value = {
			"sub": "google-user-123",
			"email": "social@example.com",
			"name": "Social User",
			"picture": "https://example.com/pic.jpg",
			"email_verified": True,
		}

		response = self.client.post(
			reverse("users-auth-google"),
			{"id_token": "google-id-token"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertFalse(response.data["requires_confirmation"])
		self.assertIn("tokens", response.data)
		self.assertTrue(User.objects.filter(email="social@example.com").exists())
		self.assertTrue(
			SocialAccount.objects.filter(
				provider=SocialAccount.PROVIDER_GOOGLE,
				provider_user_id="google-user-123",
			).exists()
		)

	@patch("apps.user.utils.google_id_token.verify_oauth2_token")
	def test_google_auth_requires_confirmation_on_email_collision(self, mock_verify):
		User.objects.create_user(
			username="existing",
			email="existing@example.com",
			password="StrongPass123!",
		)
		mock_verify.return_value = {
			"sub": "google-user-999",
			"email": "existing@example.com",
			"name": "Existing User",
			"email_verified": True,
		}

		response = self.client.post(
			reverse("users-auth-google"),
			{"id_token": "collision-token"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data["requires_confirmation"])
		self.assertIn("confirmation", response.data["detail"].lower())
		self.assertEqual(len(getattr(mail, "outbox", [])), 1)

		email_body = mail.outbox[0].body
		raw_token = email_body.split("token=")[-1].strip()
		confirm_response = self.client.post(
			reverse("users-confirm-social-link"),
			{"token": raw_token},
			format="json",
		)

		self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
		self.assertIn("tokens", confirm_response.data)
		self.assertTrue(
			SocialAccount.objects.filter(
				provider=SocialAccount.PROVIDER_GOOGLE,
				provider_user_id="google-user-999",
				user__email="existing@example.com",
			).exists()
		)

	@patch("apps.user.utils.google_id_token.verify_oauth2_token")
	def test_confirm_social_link_rejects_inactive_user(self, mock_verify):
		user = User.objects.create_user(
			username="inactive-user",
			email="inactive@example.com",
			password="StrongPass123!",
			is_active=False,
		)
		mock_verify.return_value = {
			"sub": "google-user-inactive",
			"email": "inactive@example.com",
			"name": "Inactive User",
			"email_verified": True,
		}

		response = self.client.post(
			reverse("users-auth-google"),
			{"id_token": "inactive-token"},
			format="json",
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data["requires_confirmation"])

		email_body = mail.outbox[0].body
		raw_token = email_body.split("token=")[-1].strip()
		confirm_response = self.client.post(
			reverse("users-confirm-social-link"),
			{"token": raw_token},
			format="json",
		)

		self.assertEqual(confirm_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("detail", confirm_response.data)

	@patch("apps.user.utils.google_id_token.verify_oauth2_token")
	def test_google_auth_collision_respects_confirmation_cooldown(self, mock_verify):
		User.objects.create_user(
			username="cooldown-user",
			email="cooldown@example.com",
			password="StrongPass123!",
		)
		mock_verify.return_value = {
			"sub": "google-user-cooldown",
			"email": "cooldown@example.com",
			"name": "Cooldown User",
			"email_verified": True,
		}

		url = reverse("users-auth-google")
		first_response = self.client.post(url, {"id_token": "first-token"}, format="json")
		second_response = self.client.post(url, {"id_token": "second-token"}, format="json")

		self.assertEqual(first_response.status_code, status.HTTP_200_OK)
		self.assertEqual(second_response.status_code, status.HTTP_200_OK)
		self.assertTrue(first_response.data["requires_confirmation"])
		self.assertTrue(second_response.data["requires_confirmation"])
		self.assertEqual(len(getattr(mail, "outbox", [])), 1)
		self.assertEqual(
			SocialLinkIntent.objects.filter(
				user__email="cooldown@example.com",
				provider=SocialAccount.PROVIDER_GOOGLE,
				used_at__isnull=True,
			).count(),
			1,
		)

	@patch("apps.user.utils.google_id_token.verify_oauth2_token")
	def test_link_and_unlink_social_account(self, mock_verify):
		user = User.objects.create_user(
			username="regular",
			email="regular@example.com",
			password="StrongPass123!",
		)
		self.client.force_authenticate(user=user)

		mock_verify.return_value = {
			"sub": "google-user-link-1",
			"email": "regular@example.com",
			"name": "Regular User",
			"email_verified": True,
		}

		link_response = self.client.post(
			reverse("users-linked-accounts"),
			{"provider": "google", "id_token": "id-token"},
			format="json",
		)
		self.assertEqual(link_response.status_code, status.HTTP_200_OK)

		list_response = self.client.get(reverse("users-linked-accounts"))
		self.assertEqual(list_response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(list_response.data), 1)

		unlink_response = self.client.delete(
			reverse("users-unlink-linked-account", kwargs={"provider": "google"})
		)
		self.assertEqual(unlink_response.status_code, status.HTTP_204_NO_CONTENT)

	@patch("apps.user.utils.requests.get")
	def test_facebook_auth_returns_jwt(self, mock_get):
		# First call returns profile, second call returns debug_token payload
		mock_profile = Mock()
		mock_profile.status_code = 200
		mock_profile.json.return_value = {
			"id": "facebook-user-123",
			"name": "FB User",
			"email": "fbuser@example.com",
			"picture": {"data": {"url": "https://example.com/fb.jpg"}},
		}
		mock_debug = Mock()
		mock_debug.status_code = 200
		mock_debug.json.return_value = {
			"data": {"is_valid": True, "app_id": "test-fb-app-id", "user_id": "facebook-user-123"}
		}
		mock_get.side_effect = [mock_profile, mock_debug]

		response = self.client.post(
			reverse("users-auth-facebook"),
			{"access_token": "fb-access-token"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("tokens", response.data)
		self.assertTrue(
			SocialAccount.objects.filter(
				provider=SocialAccount.PROVIDER_FACEBOOK,
				provider_user_id="facebook-user-123",
			).exists()
		)
