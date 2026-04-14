from django.test import TestCase, Client
from django.urls import reverse
from .models import Session, Event, Issue
import json

class CaptureErrorTest(TestCase):
    def setUp(self):
        self.client = Client()
        # URL is /api/capture/ based on config/urls.py and tracker/urls.py
        self.url = '/api/capture/'

    def test_capture_error_existing_session(self):
        # Create a session
        session_id = "test_session_123"
        Session.objects.create(session_id=session_id)
        
        data = {
            "type": "TestError",
            "message": "Something went wrong",
            "session_id": session_id
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Session.objects.count(), 1)
        event = Event.objects.first()
        self.assertEqual(event.session.session_id, session_id)

    def test_capture_error_new_session(self):
        session_id = "new_session_456"
        
        data = {
            "type": "TestError",
            "message": "Something went wrong",
            "session_id": session_id
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(Session.objects.first().session_id, session_id)
