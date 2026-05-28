from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


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
		self.assertEqual(mail.outbox[0].subject, "Welcome to Studyzone")

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
