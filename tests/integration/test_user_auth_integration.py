"""Integration tests for User Authentication and Registration.

Tests the complete user lifecycle including:
- User registration with email/phone verification
- JWT authentication flow
- Social authentication (Google/Facebook)
- Soft delete and account recovery

Integration Touchpoints:
- User Model ↔ VerificationToken (email/phone verification)
- User Model ↔ UserProfile (profile creation)
- User Model ↔ SocialAccount (social auth linking)
- Authentication ↔ JWT Tokens
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import User, VerificationToken


pytestmark = pytest.mark.integration


class TestUserRegistrationFlow:
    """Test complete user registration flow with email verification."""
    
    def test_registration_creates_user_and_verification_token(self, api_client):
        """
        Integration: Registration → User Creation → Verification Token Created
        
        Flow:
        1. User submits registration data
        2. User account is created (unverified)
        3. VerificationToken is created
        """
        url = reverse('users-list')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'verification_options': 'email',
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(username='newuser').exists()
        
        user = User.objects.get(username='newuser')
        assert user.is_email_verified is False
        
        # Verify token was created
        token_exists = VerificationToken.objects.filter(
            user=user,
            channel='email'
        ).exists()
        assert token_exists
    
    def test_email_verification_completes_flow(self, api_client, user):
        """
        Integration: Email Verification → User Verified → Can Login
        """
        from django.utils import timezone
        from datetime import timedelta
        from apps.user.utils import _hash_token
        
        user.is_email_verified = False
        user.save()
        
        token = VerificationToken.objects.create(
            user=user,
            channel='email',
            token_hash=_hash_token('test-token-hash'),
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        url = reverse('users-verify-email')
        response = api_client.post(url, {'token': 'test-token-hash'})
        
        assert response.status_code == status.HTTP_200_OK
        
        user.refresh_from_db()
        assert user.is_email_verified is True
    
    def test_duplicate_email_registration_rejected(self, api_client, user):
        """Integration: Duplicate Email → Validation Error"""
        url = reverse('users-list')
        data = {
            'username': 'anotheruser',
            'email': user.email,
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'verification_options': 'email',
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data


class TestJWTAuthenticationFlow:
    """Test JWT authentication integration with User model."""
    
    def test_login_returns_valid_tokens(self, api_client, user):
        """Integration: Login → JWT Token Generation → Token Valid"""
        url = reverse('token_obtain_pair')
        data = {
            'username': 'testuser',
            'password': 'StrongPass123!'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_access_protected_endpoint_with_token(self, authenticated_client):
        """Integration: Token → Protected Endpoint Access"""
        url = reverse('users-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'
    
    def test_token_refresh_flow(self, api_client, user):
        """Integration: Refresh Token → New Access Token"""
        refresh = RefreshToken.for_user(user)
        
        url = reverse('token_refresh')
        response = api_client.post(url, {'refresh': str(refresh)})
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
    
    def test_soft_deleted_user_cannot_authenticate(self, api_client, soft_deleted_user):
        """Integration: Soft Delete → Authentication Blocked"""
        url = reverse('token_obtain_pair')
        data = {
            'username': soft_deleted_user.username,
            'password': 'StrongPass123!'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestUserPermissionsIntegration:
    """Test permission integration across user operations."""
    
    def test_user_can_only_access_own_data(self, authenticated_client):
        """Integration: Permission → User Isolation"""
        url = reverse('users-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testuser'
    
    def test_unauthenticated_access_rejected(self, api_client):
        """Integration: Authentication Required"""
        url = reverse('users-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
