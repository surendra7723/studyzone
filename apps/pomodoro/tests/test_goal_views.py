from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pomodoro.models import Goal

User = get_user_model()


class GoalApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="StrongPass123!"
        )
        self.other_user = User.objects.create_user(
            username="bob", password="StrongPass123!"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_goal(self):
        response = self.client.post(
            reverse("pomodoro:goal-list"),
            {"title": "Read Book", "target_date": "2026-12-31"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(Goal.objects.first().user, self.user)

    def test_list_goals_filters_by_user(self):
        Goal.objects.create(
            user=self.user, title="Alice Goal", target_date="2026-12-31"
        )
        Goal.objects.create(
            user=self.other_user, title="Bob Goal", target_date="2026-12-31"
        )
        response = self.client.get(reverse("pomodoro:goal-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Alice Goal")

    def test_retrieve_goal(self):
        goal = Goal.objects.create(
            user=self.user, title="Read Book", target_date="2026-12-31"
        )
        response = self.client.get(
            reverse("pomodoro:goal-detail", args=[goal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Read Book")

    def test_update_goal(self):
        goal = Goal.objects.create(
            user=self.user, title="Read Book", target_date="2026-12-31"
        )
        response = self.client.put(
            reverse("pomodoro:goal-detail", args=[goal.id]),
            {
                "title": "Read Two Books",
                "target_date": "2026-12-31",
                "description": "Updated",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.title, "Read Two Books")

    def test_partial_update_goal(self):
        goal = Goal.objects.create(
            user=self.user, title="Read Book", target_date="2026-12-31"
        )
        response = self.client.patch(
            reverse("pomodoro:goal-detail", args=[goal.id]),
            {"title": "Read Two Books"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        goal.refresh_from_db()
        self.assertEqual(goal.title, "Read Two Books")

    def test_delete_goal(self):
        goal = Goal.objects.create(
            user=self.user, title="Read Book", target_date="2026-12-31"
        )
        response = self.client.delete(
            reverse("pomodoro:goal-detail", args=[goal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Goal.objects.count(), 0)

    def test_goal_ordering_by_target_date(self):
        Goal.objects.create(
            user=self.user, title="A", target_date="2026-01-01"
        )
        Goal.objects.create(
            user=self.user, title="B", target_date="2026-01-02"
        )
        Goal.objects.create(
            user=self.user, title="C", target_date="2026-01-01"
        )
        response = self.client.get(reverse("pomodoro:goal-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["title"], "A")
        self.assertEqual(results[1]["title"], "C")
        self.assertEqual(results[2]["title"], "B")

    def test_create_goal_with_past_target_date(self):
        response = self.client.post(
            reverse("pomodoro:goal-list"),
            {"title": "Old Goal", "target_date": "2020-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_goal_with_empty_title_returns_400(self):
        response = self.client.post(
            reverse("pomodoro:goal-list"),
            {"title": "", "target_date": "2026-12-31"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_modify_other_users_goal(self):
        goal = Goal.objects.create(
            user=self.other_user, title="Bob Goal", target_date="2026-12-31"
        )
        response = self.client.patch(
            reverse("pomodoro:goal-detail", args=[goal.id]),
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_goal_completion_toggle(self):
        goal = Goal.objects.create(
            user=self.user, title="Read Book", target_date="2026-12-31"
        )
        response = self.client.post(
            reverse("pomodoro:goal-toggle", args=[goal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_completed"])
        response = self.client.post(
            reverse("pomodoro:goal-toggle", args=[goal.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_completed"])

    def test_goal_list_pagination(self):
        for i in range(25):
            Goal.objects.create(
                user=self.user, title=f"Goal {i}", target_date="2026-12-31"
            )
        response = self.client.get(reverse("pomodoro:goal-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 20)
