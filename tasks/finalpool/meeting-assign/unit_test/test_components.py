#!/usr/bin/env python3
"""
Unit tests for individual evaluation components of meeting-assign task
Tests remote email verification functions and edge cases
"""

import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

# Import evaluation functions
try:
    from check_remote import check_sent_email, simulate_remote_check, get_gmail_service, GOOGLE_LIBS_AVAILABLE
    REMOTE_AVAILABLE = True
except ImportError:
    REMOTE_AVAILABLE = False
    GOOGLE_LIBS_AVAILABLE = False

class TestRemoteEmailVerification(unittest.TestCase):
    """Test remote email verification functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Mock Gmail service and message structure
        self.mock_message = {
            'id': 'test123',
            'internalDate': str(int(1640995200000)),  # Mock timestamp
            'payload': {
                'mimeType': 'text/plain',
                'body': {
                    'data': self.encode_email_body(
                        "Meeting time: 周二下午14:00到16:00. Participants: jinghanz, junteng, Junxian, shiqi, Ting Wu, Wei Liu, Weihao Zeng, YANG Cheng, 童雨轩, 黄裕振"
                    )
                }
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def encode_email_body(self, text):
        """Helper to encode email body like Gmail API"""
        import base64
        return base64.urlsafe_b64encode(text.encode('utf-8')).decode('utf-8')
    
    @unittest.skipUnless(REMOTE_AVAILABLE and GOOGLE_LIBS_AVAILABLE, "Remote check module or Google libs not available")
    def test_valid_email_verification_passes(self):
        """Test that valid email passes remote verification"""
        # Mock Gmail service
        mock_service = Mock()
        mock_service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'test123'}]
        }
        mock_service.users().messages().get().execute.return_value = self.mock_message
        
        success, message = check_sent_email(mock_service)
        self.assertTrue(success, f"Valid email should pass verification: {message}")
        self.assertIn("verification successful", message.lower())
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_no_emails_found_fails(self):
        """Test that no emails found fails verification"""
        # Mock Gmail service returning no messages
        mock_service = Mock()
        mock_service.users().messages().list().execute.return_value = {
            'messages': []
        }
        
        success, message = check_sent_email(mock_service)
        self.assertFalse(success, "No emails should fail verification")
        self.assertIn("No emails found", message)
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_wrong_time_format_fails(self):
        """Test that wrong time format fails verification"""
        # Create message with wrong time format
        wrong_time_message = self.mock_message.copy()
        wrong_time_message['payload']['body']['data'] = self.encode_email_body(
            "Meeting time: Monday 2:00 PM. Participants: jinghanz, junteng, Junxian, shiqi, Ting Wu, Wei Liu, Weihao Zeng, YANG Cheng, 童雨轩, 黄裕振"
        )
        
        mock_service = Mock()
        mock_service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'test123'}]
        }
        mock_service.users().messages().get().execute.return_value = wrong_time_message
        
        success, message = check_sent_email(mock_service)
        self.assertFalse(success, "Wrong time format should fail verification")
        self.assertIn("time format not found", message.lower())
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_missing_participants_fails(self):
        """Test that missing participants fail verification"""
        # Create message with missing participants
        missing_participants_message = self.mock_message.copy()
        missing_participants_message['payload']['body']['data'] = self.encode_email_body(
            "Meeting time: 周二下午14:00到16:00. Participants: jinghanz, junteng"  # Missing most participants
        )
        
        mock_service = Mock()
        mock_service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'test123'}]
        }
        mock_service.users().messages().get().execute.return_value = missing_participants_message
        
        success, message = check_sent_email(mock_service)
        self.assertFalse(success, "Missing participants should fail verification")
        self.assertIn("Missing participants", message)
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_alternative_time_format_passes(self):
        """Test that alternative time format passes verification"""
        # Create message with alternative time format
        alt_time_message = self.mock_message.copy()
        alt_time_message['payload']['body']['data'] = self.encode_email_body(
            "Meeting time: 周二下午2:00到4:00. Participants: jinghanz, junteng, Junxian, shiqi, Ting Wu, Wei Liu, Weihao Zeng, YANG Cheng, 童雨轩, 黄裕振"
        )
        
        mock_service = Mock()
        mock_service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'test123'}]
        }
        mock_service.users().messages().get().execute.return_value = alt_time_message
        
        success, message = check_sent_email(mock_service)
        self.assertTrue(success, f"Alternative time format should pass: {message}")
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_simulate_remote_check(self):
        """Test the simulation function"""
        success, message = simulate_remote_check()
        self.assertTrue(success, "Simulation should always pass")
        self.assertIn("verification completed", message.lower())
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_gmail_service_unavailable_simulation(self):
        """Test that None service triggers simulation"""
        success, message = check_sent_email(None)
        self.assertTrue(success, "Simulation should pass")
        self.assertIn("Simulated", message)

class TestGmailServiceSetup(unittest.TestCase):
    """Test Gmail service setup and error handling"""
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    @patch('check_remote.os.path.exists', return_value=False)
    def test_no_credentials_returns_none(self, mock_exists):
        """Test that missing credentials returns None"""
        service = get_gmail_service()
        self.assertIsNone(service, "Should return None when no credentials available")
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    @patch('check_remote.build')
    @patch('check_remote.Credentials.from_authorized_user_file')
    @patch('check_remote.os.path.exists', return_value=True)
    def test_valid_credentials_returns_service(self, mock_exists, mock_creds, mock_build):
        """Test that valid credentials return service"""
        # Mock valid credentials
        mock_cred_obj = Mock()
        mock_cred_obj.valid = True
        mock_creds.return_value = mock_cred_obj
        
        # Mock successful service build
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        service = get_gmail_service()
        
        # Should attempt to build service
        mock_build.assert_called_once()

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_gmail_api_error_handled(self):
        """Test handling of Gmail API errors"""
        from googleapiclient.errors import HttpError
        
        # Mock service that raises HttpError
        mock_service = Mock()
        mock_service.users().messages().list().execute.side_effect = HttpError(
            resp=Mock(status=403), content=b'Forbidden'
        )
        
        success, message = check_sent_email(mock_service)
        self.assertFalse(success, "API error should fail verification")
        self.assertIn("Gmail API error", message)
    
    @unittest.skipUnless(REMOTE_AVAILABLE, "Remote check module not available")
    def test_multipart_email_parsing(self):
        """Test parsing of multipart emails"""
        # Create multipart message structure
        multipart_message = {
            'id': 'test123',
            'internalDate': str(int(1640995200000)),
            'payload': {
                'mimeType': 'multipart/mixed',
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': self.encode_email_body(
                                "Meeting time: 周二下午14:00到16:00. Participants: jinghanz, junteng, Junxian, shiqi, Ting Wu, Wei Liu, Weihao Zeng, YANG Cheng, 童雨轩, 黄裕振"
                            )
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {'data': 'html_content'}
                    }
                ]
            }
        }
        
        mock_service = Mock()
        mock_service.users().messages().list().execute.return_value = {
            'messages': [{'id': 'test123'}]
        }
        mock_service.users().messages().get().execute.return_value = multipart_message
        
        success, message = check_sent_email(mock_service)
        self.assertTrue(success, f"Multipart email should be parsed correctly: {message}")
    
    def encode_email_body(self, text):
        """Helper to encode email body like Gmail API"""
        import base64
        return base64.urlsafe_b64encode(text.encode('utf-8')).decode('utf-8')

def run_unit_tests():
    """Run all unit tests with colored output"""
    
    print("🧪 Meeting Assign - Remote Check Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRemoteEmailVerification))
    suite.addTests(loader.loadTestsFromTestCase(TestGmailServiceSetup))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ ALL UNIT TESTS PASSED ({result.testsRun} tests)")
    else:
        print(f"❌ SOME TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        for test, error in result.failures + result.errors:
            print(f"   {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)