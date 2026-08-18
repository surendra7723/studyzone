from django.test import TestCase

from apps.ambience.models import Category, AmbienceTrack


class AmbienceModelTest(TestCase):
    def test_category_str(self):
        category = Category(name="Rain")
        self.assertEqual(str(category), "Rain")

    def test_track_str(self):
        track = AmbienceTrack(name="Rain Sounds")
        self.assertEqual(str(track), "Rain Sounds")

    def test_track_defaults_to_active(self):
        category = Category.objects.create(name="Rain")
        track = AmbienceTrack.objects.create(
            name="Rain Sounds", category=category, duration_seconds=60
        )
        self.assertTrue(track.is_active)

    def test_category_name_uniqueness(self):
        Category.objects.create(name="Rain")
        duplicate = Category(name="Rain")
        with self.assertRaises(Exception):
            duplicate.full_clean()
