from typing import Optional
from django.utils import timezone
from rest_framework import serializers

from ..models import Task, Category


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'color', 'created_at', 'updated_at', 'task_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_task_count(self, obj: Category) -> int:
        """Get the number of tasks in this category."""
        return obj.tasks.count() if hasattr(obj, 'tasks') else 0
    
    def validate_name(self, value):
        """Validate category name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Category name cannot be empty.")
        
        user = self.context['request'].user
        existing = Category.objects.filter(user=user, name__iexact=value.strip())
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        if existing.exists():
            raise serializers.ValidationError("You already have a category with this name.")
        
        return value.strip()


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'category', 'category_name',
            'priority', 'due_date', 'estimated_pomodoros',
            'is_completed', 'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_overdue']
    
    def get_is_overdue(self, obj: Task) -> bool:
        """Check if task is overdue."""
        if obj.due_date and not obj.is_completed:
            return obj.due_date < timezone.now()
        return False
    
    def validate_title(self, value):
        """Validate task title."""
        if not value or not value.strip():
            raise serializers.ValidationError("Task title cannot be empty.")
        return value.strip()
    
    def validate_due_date(self, value):
        """Validate due date."""
        if value and value < timezone.now():
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value
    
    def validate_estimated_pomodoros(self, value):
        """Validate estimated pomodoros."""
        if value < 1:
            raise serializers.ValidationError("Estimated pomodoros must be at least 1.")
        if value > 100:
            raise serializers.ValidationError("Estimated pomodoros cannot exceed 100.")
        return value
    
    def validate(self, attrs):
        """Cross-field validation."""
        if attrs.get('category'):
            user = self.context['request'].user
            if attrs['category'].user != user:
                raise serializers.ValidationError({
                    'category': 'Category must belong to you.'
                })
        return attrs
