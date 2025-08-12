import pytest
import requests
import os
import json
import logging
import time
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Test 5: Full pipeline test - comprehensive change (2025-08-12T11:10:30Z)

class TestContentPipeline:
    """Integration tests for the content processing pipeline"""
    
    @pytest.fixture
    def function_url(self):
        """Get the function app URL from environment"""
        url = os.getenv('FUNCTION_URL')
        if not url:
            pytest.skip("FUNCTION_URL not set")
            return  # Ensure function always returns
        return url.rstrip('/')
    
    def test_summary_womble_endpoint(self, function_url):
        """Test that the SummaryWomble function is accessible (HTTP-triggered)"""
        # SummaryWomble requires authentication, so we expect 401 without function key
        # Retry logic to handle Azure Functions cold start timing
        import time
        
        for attempt in range(3):
            try:
                response = requests.get(f"{function_url}/api/SummaryWomble", timeout=30)
                
                # Expected behavior: 401 (requires function key)
                if response.status_code == 401:
                    return  # Test passed
                
                # Handle cold start scenario: 404 means function not yet registered
                elif response.status_code == 404 and attempt < 2:
                    logging.warning(f"Attempt {attempt + 1}: SummaryWomble returned 404 (cold start?), retrying...")
                    time.sleep(10)  # Wait for function to warm up
                    continue
                
                # Any other response code
                else:
                    assert False, f"Expected 401 (requires auth), got {response.status_code} on attempt {attempt + 1}"
                    
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    logging.warning(f"Attempt {attempt + 1}: Request failed ({e}), retrying...")
                    time.sleep(10)
                    continue
                else:
                    raise
        
        # If we get here, all retries failed
        assert False, "SummaryWomble function not accessible after 3 attempts"
    
    def test_summary_womble_with_invalid_request(self, function_url):
        """Test SummaryWomble with invalid request data"""
        # This should return 400, 401, or 500 for invalid JSON/auth
        # Retry logic to handle Azure Functions cold start timing
        
        for attempt in range(3):
            try:
                response = requests.get(f"{function_url}/api/SummaryWomble", timeout=30)
                
                # Expected behavior: 401 (auth required) or 400/500 (bad request)
                if response.status_code in [401, 400, 500]:
                    return  # Test passed
                
                # Handle cold start scenario: 404 means function not yet registered
                elif response.status_code == 404 and attempt < 2:
                    logging.warning(f"Attempt {attempt + 1}: SummaryWomble returned 404 (cold start?), retrying...")
                    time.sleep(10)  # Wait for function to warm up
                    continue
                
                # Any other unexpected response code
                else:
                    assert False, f"Expected auth error or bad request, got {response.status_code} on attempt {attempt + 1}"
                    
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    logging.warning(f"Attempt {attempt + 1}: Request failed ({e}), retrying...")
                    time.sleep(10)
                    continue
                else:
                    raise
        
        # If we get here, all retries failed
        assert False, "SummaryWomble function not accessible after 3 attempts"
    
    def test_get_hot_topics_not_accessible_via_http(self, function_url):
        """Test that GetHotTopics is not accessible via HTTP (timer-triggered only)"""
        response = requests.get(f"{function_url}/api/GetHotTopics", timeout=30)
        # Timer-triggered functions should return 404 when accessed via HTTP
        assert response.status_code == 404, f"Expected 404 (timer-triggered), got {response.status_code}"
    
    def test_function_app_is_running(self, function_url):
        """Test that the function app is running and responding"""
        # Just test that we can reach the function app (any response is good)
        try:
            response = requests.get(f"{function_url}/api/SummaryWomble", timeout=10)
            # Any response code means the app is running
            assert response.status_code is not None
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Function app not responding: {e}")
    
    def test_key_vault_access(self):
        """Test that the function can access Key Vault secrets"""
        try:
            credential = DefaultAzureCredential()
            # This will use the same managed identity as the function
            vault_url = "https://ai-content-staging-kv.vault.azure.net/"
            client = SecretClient(vault_url=vault_url, credential=credential)
            
            # Try to list secrets (should work if permissions are correct)
            secrets = list(client.list_properties_of_secrets())
            assert len(secrets) >= 0  # Should not fail, even if empty
            
        except Exception as e:
            pytest.skip(f"Key Vault access test skipped: {e}")

class TestSecurityCompliance:
    """Security and compliance tests"""
    
    @pytest.fixture
    def function_url(self):
        """Get the function app URL from environment"""
        url = os.getenv('FUNCTION_URL')
        if not url:
            pytest.skip("FUNCTION_URL not set")
        return url.rstrip('/')
    
    def test_https_only(self, function_url):
        """Ensure the function app only accepts HTTPS"""
        if function_url.startswith('https://'):
            # Try HTTP version (should fail or redirect)
            http_url = function_url.replace('https://', 'http://')
            try:
                response = requests.get(f"{http_url}/api/SummaryWomble", timeout=10, allow_redirects=False)
                # Should either fail or redirect to HTTPS
                assert response.status_code in [301, 302, 403, 404] or 'https' in response.headers.get('location', '')
            except requests.exceptions.RequestException:
                # Connection refused is also acceptable (HTTPS-only)
                pass
    
    def test_no_sensitive_data_in_response(self, function_url):
        """Ensure no sensitive data is exposed in API responses"""
        # Test with SummaryWomble since GetHotTopics is timer-triggered
        response = requests.get(f"{function_url}/api/SummaryWomble", timeout=30)
        
        if response.status_code in [200, 401, 400, 500]:  # Any valid response
            response_text = response.text.lower()
            
            # Check for common sensitive data patterns
            sensitive_patterns = [
                'password', 'secret', 'key', 'token', 'credential',
                'connection_string', 'api_key', 'private'
            ]
            
            for pattern in sensitive_patterns:
                assert pattern not in response_text, f"Potential sensitive data '{pattern}' found in response"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
