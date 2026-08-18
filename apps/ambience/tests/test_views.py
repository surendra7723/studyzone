from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ambience.models import Category, AmbienceTrack


class AmbienceViewTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Rain")
        self.active_track = AmbienceTrack.objects.create(
            name="Rain Sounds",
            category=self.category,
            duration_seconds=60,
            is_active=True,
        )
        self.inactive_track = AmbienceTrack.objects.create(
            name="Old Sounds",
            category=self.category,
            duration_seconds=60,
            is_active=False,
        )

    def test_list_active_tracks(self):
        response = self.client.get(reverse("ambience:track-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Rain Sounds")

    def test_filter_tracks_by_category(self):
        response = self.client.get(
            reverse("ambience:track-list"), {"category": self.category.name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Rain Sounds")

    def test_list_categories(self):
        response = self.client.get(reverse("ambience:category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Rain")

    def test_inactive_tracks_excluded(self):
        response = self.client.get(reverse("ambience:track-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [track["name"] for track in response.data["results"]]
        self.assertNotIn("Old Sounds", names)

    def test_track_list_pagination(self):
        for i in range(25):
            AmbienceTrack.objects.create(
                name=f"Track {i}",
                category=self.category,
                duration_seconds=60,
                is_active=True,
            )
        response = self.client.get(reverse("ambience:track-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 20)

    def test_track_filter_requires_valid_category(self):
        response = self.client.get(
            reverse("ambience:track-list"), {"category": 9999}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_unauthenticated_can_list_tracks(self):
        response = self.client.get(reverse("ambience:track-list"))
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_can_list_categories(self):
        response = self.client.get(reverse("ambience:category-list"))
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
