"""Integration tests for Tasks and Pomodoro features.

Tests the interaction between Tasks, Categories, and Pomodoro Sessions.
"""
import pytest
from django.urls import reverse
from rest_framework import status

from apps.tasks.models import Task, Category
from apps.pomodoro.models import PomodoroSession, TaskSession, Goal


pytestmark = pytest.mark.integration


class TestTaskCategoryIntegration:
    """Test Task-Category integration."""
    
    def test_category_user_isolation(self, authenticated_client, other_category):
        """Users can only see their own categories."""
        url = reverse('tasks:category-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        names = [c['name'] for c in response.data]
        assert other_category.name not in names
    
    def test_create_task_with_category(self, authenticated_client, category):
        """Task can be created with user's own category."""
        url = reverse('tasks:task-list')
        data = {'title': 'New Task', 'category': category.id, 'priority': 2}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_task_with_other_user_category_rejected(self, authenticated_client, other_category):
        """Cannot use another user's category."""
        url = reverse('tasks:task-list')
        data = {'title': 'Task', 'category': other_category.id, 'priority': 2}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_category_deletion_nullifies_tasks(self, authenticated_client, category, task):
        """Deleting category sets task.category to null."""
        url = reverse('tasks:category-detail', kwargs={'pk': category.pk})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        task.refresh_from_db()
        assert task.category is None


class TestTaskBulkOperations:
    """Test bulk operations for tasks."""
    
    def test_bulk_create_tasks(self, authenticated_client, category):
        """Bulk create multiple tasks."""
        url = reverse('tasks:task-bulk-create')
        data = [
            {'title': 'Task 1', 'category': category.id},
            {'title': 'Task 2', 'category': category.id},
        ]
        
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data) == 2
    
    def test_bulk_update_tasks(self, authenticated_client, multiple_tasks):
        """Bulk update multiple tasks."""
        url = reverse('tasks:task-bulk-update')
        data = [{'id': multiple_tasks[0].id, 'is_completed': True}]
        
        response = authenticated_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK


class TestPomodoroTaskSessionIntegration:
    """Test Pomodoro Session ↔ Task Session integration."""
    
    def test_create_session_linked_to_task(self, authenticated_client, task):
        """Session can be created for a task."""
        url = reverse('pomodoro:pomodoro-session-list')
        data = {'session_type': 'focus', 'active_minutes': 25, 'break_minutes': 5}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        
        session = PomodoroSession.objects.get(id=response.data['id'])
        assert session.user == task.user
    
    def test_task_session_validates_ownership(self, other_user, task, pomodoro_session):
        """Cannot link task from different user."""
        from django.core.exceptions import ValidationError
        
        pomodoro_session.user = other_user
        pomodoro_session.save()
        
        ts = TaskSession(task=task, pomodoro_session=pomodoro_session, duration_minutes=25)
        
        with pytest.raises(ValidationError):
            ts.full_clean()


class TestPomodoroGoalIntegration:
    """Test Goal management."""
    
    def test_create_goal(self, authenticated_client):
        """Create a pomodoro goal."""
        from datetime import date, timedelta
        
        url = reverse('pomodoro:goal-list')
        data = {
            'title': 'Study Goal',
            'target_date': str(date.today() + timedelta(days=30))
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_goals_user_isolated(self, authenticated_client, goal, other_user):
        """Goals are user-isolated."""
        Goal.objects.create(user=other_user, title='Other', target_date=goal.target_date)
        
        url = reverse('pomodoro:goal-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
