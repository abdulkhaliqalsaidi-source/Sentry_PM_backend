"""
Property-Based Tests for chat-notifications-enhancement
Uses Hypothesis for property testing.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.django import TestCase

from project_management.models import Project, ProjectMessage, MessageReaction

User = get_user_model()


class ReactionUniquenessPropertyTest(TestCase):
    """
    الخاصية 1: فريدية التفاعل (Reaction Uniqueness)
    Validates: Requirements 1.1

    لأي مجموعة من (رسالة، مستخدم، emoji)، يجب أن يكون هناك سجل واحد فقط
    في MessageReaction. محاولة إدراج نفس الثلاثي مرتين يجب أن تُفشل بخطأ integrity.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser_reaction',
            password='testpass123'
        )
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user
        )
        self.message = ProjectMessage.objects.create(
            project=self.project,
            sender=self.user,
            content='Hello world'
        )

    @given(st.text(min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_reaction_uniqueness(self, emoji):
        """
        الخاصية 1: فريدية التفاعل
        Validates: Requirements 1.1

        Inserting the same (message, user, emoji) triple twice must raise IntegrityError.
        """
        # First insertion should succeed
        MessageReaction.objects.create(
            message=self.message,
            user=self.user,
            emoji=emoji
        )

        # Second insertion of the same triple must raise IntegrityError
        with self.assertRaises(IntegrityError):
            MessageReaction.objects.create(
                message=self.message,
                user=self.user,
                emoji=emoji
            )
