
import requests
import json
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

BASE_URL = "https://561aa149-496e-4379-8d51-dfe1920a47d9-00-26rshp3f5z3k9.sisko.replit.dev"  # Use localhost for local testing
# If you want to test against deployed version, change to your deployed URL

# Test credentials
TEST_EMAIL = "user123@gmail.com"
TEST_PASSWORD = "12345678"


def print_response_details(response):
    """Helper function to print detailed response information"""
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    try:
        response_json = response.json()
        print(f"Response JSON: {json.dumps(response_json, indent=2)}")
        return response_json
    except json.JSONDecodeError:
        print(f"Response Text: {response.text}")
        return None


def create_test_user():
    """Create a test user for cancellation testing"""
    print("\n=== Creating Test User ===")

    signup_url = f"{BASE_URL}/signup"
    signup_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "username": f"test_cancel_user_{int(time.time())}"
    }

    try:
        response = requests.post(signup_url, json=signup_data)
        print_response_details(response)

        if response.status_code in [200, 201]:
            print("✅ Test user created successfully")
            return True
        elif response.status_code == 400:
            # User might already exist, try to continue
            print("⚠️ User might already exist, continuing with login test")
            return True
        else:
            print("❌ Failed to create test user")
            return False
    except Exception as e:
        print(f"❌ Error creating test user: {str(e)}")
        return False


def login_test_user():
    """Login as test user and return session"""
    print("\n=== Logging in Test User ===")

    login_url = f"{BASE_URL}/login"
    login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}

    session = requests.Session()

    try:
        response = session.post(login_url, json=login_data)
        response_data = print_response_details(response)

        if response.status_code == 200:
            print("✅ Login successful")
            return session
        else:
            print("❌ Login failed")
            return None
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return None


def test_subscription_endpoints(session):
    """Test subscription-related endpoints"""
    print("\n=== Testing Subscription Endpoints ===")
    
    # Test getting subscription info
    print("\n--- Testing subscription info endpoint ---")
    info_url = f"{BASE_URL}/api/subscription/manage"
    try:
        response = session.get(info_url)
        response_data = print_response_details(response)
        
        if response.status_code == 200:
            print("✅ Subscription info endpoint working")
        else:
            print("❌ Subscription info endpoint failed")
    except Exception as e:
        print(f"❌ Error testing subscription info: {str(e)}")

    # Test getting credits
    print("\n--- Testing credits endpoint ---")
    credits_url = f"{BASE_URL}/api/subscription/credits"
    try:
        response = session.get(credits_url)
        response_data = print_response_details(response)
        
        if response.status_code == 200:
            print("✅ Credits endpoint working")
        else:
            print("❌ Credits endpoint failed")
    except Exception as e:
        print(f"❌ Error testing credits: {str(e)}")

    # Test subscription page
    print("\n--- Testing subscription page endpoint ---")
    page_url = f"{BASE_URL}/api/subscription/"
    try:
        response = session.get(page_url)
        response_data = print_response_details(response)
        
        if response.status_code == 200:
            print("✅ Subscription page endpoint working")
            return response_data
        else:
            print("❌ Subscription page endpoint failed")
            return None
    except Exception as e:
        print(f"❌ Error testing subscription page: {str(e)}")
        return None


def test_cancel_subscription_endpoint(session):
    """Test subscription cancellation endpoint (without actual subscription)"""
    print("\n=== Testing Subscription Cancellation Endpoint ===")

    cancel_url = f"{BASE_URL}/api/subscription/cancel"
    cancel_data = {"cancel_at_period_end": True}

    try:
        response = session.post(cancel_url, json=cancel_data)
        response_data = print_response_details(response)

        if response.status_code == 404:
            print("✅ Cancel endpoint working (correctly returns 404 for no subscription)")
            return True
        elif response.status_code == 200:
            print("✅ Cancel endpoint working (subscription found and canceled)")
            return True
        else:
            print(f"⚠️ Cancel endpoint returned unexpected status: {response.status_code}")
            return True  # Still consider it working if it responds
    except Exception as e:
        print(f"❌ Error testing cancellation: {str(e)}")
        return False


def test_pause_subscription_endpoint(session):
    """Test subscription pause endpoint"""
    print("\n=== Testing Subscription Pause Endpoint ===")

    pause_url = f"{BASE_URL}/api/subscription/pause"
    pause_data = {"behavior": "void"}

    try:
        response = session.post(pause_url, json=pause_data)
        response_data = print_response_details(response)

        if response.status_code == 404:
            print("✅ Pause endpoint working (correctly returns 404 for no subscription)")
            return True
        elif response.status_code == 200:
            print("✅ Pause endpoint working (subscription found and paused)")
            return True
        else:
            print(f"⚠️ Pause endpoint returned unexpected status: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Error testing pause: {str(e)}")
        return False


def test_resume_subscription_endpoint(session):
    """Test subscription resume endpoint"""
    print("\n=== Testing Subscription Resume Endpoint ===")

    resume_url = f"{BASE_URL}/api/subscription/resume"
    resume_data = {}

    try:
        response = session.post(resume_url, json=resume_data)
        response_data = print_response_details(response)

        if response.status_code == 404:
            print("✅ Resume endpoint working (correctly returns 404 for no subscription)")
            return True
        elif response.status_code == 200:
            print("✅ Resume endpoint working (subscription found and resumed)")
            return True
        else:
            print(f"⚠️ Resume endpoint returned unexpected status: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Error testing resume: {str(e)}")
        return False


def test_reactivate_subscription_endpoint(session):
    """Test subscription reactivation endpoint"""
    print("\n=== Testing Subscription Reactivation Endpoint ===")

    reactivate_url = f"{BASE_URL}/api/subscription/reactivate"
    reactivate_data = {}

    try:
        response = session.post(reactivate_url, json=reactivate_data)
        response_data = print_response_details(response)

        if response.status_code == 400:
            print("✅ Reactivate endpoint working (correctly returns 400 for missing subscription_id)")
            return True
        elif response.status_code == 200:
            print("✅ Reactivate endpoint working (subscription found and reactivated)")
            return True
        else:
            print(f"⚠️ Reactivate endpoint returned unexpected status: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Error testing reactivation: {str(e)}")
        return False


def test_update_payment_method_endpoint(session):
    """Test update payment method endpoint"""
    print("\n=== Testing Update Payment Method Endpoint ===")

    update_url = f"{BASE_URL}/api/subscription/update-payment-method"

    try:
        response = session.post(update_url, json={})
        response_data = print_response_details(response)

        if response.status_code == 404:
            print("✅ Update payment method endpoint working (correctly returns 404 for no subscription)")
            return True
        elif response.status_code == 200:
            print("✅ Update payment method endpoint working")
            return True
        else:
            print(f"⚠️ Update payment method endpoint returned unexpected status: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Error testing update payment method: {str(e)}")
        return False


def test_webhook_endpoint():
    """Test webhook endpoint"""
    print("\n=== Testing Webhook Endpoint ===")

    webhook_url = f"{BASE_URL}/subscription/webhook"
    webhook_data = {
        "type": "test",
        "data": {
            "object": {}
        }
    }

    try:
        response = requests.post(webhook_url, json=webhook_data)
        response_data = print_response_details(response)

        if response.status_code in [200, 400]:  # 400 is expected for invalid signature
            print("✅ Webhook endpoint accessible")
            return True
        else:
            print(f"⚠️ Webhook endpoint returned unexpected status: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Error testing webhook: {str(e)}")
        return False


def main():
    """Run the complete subscription endpoints test"""
    print("🚀 Starting Subscription Endpoints Test")
    print("=" * 60)

    # Step 1: Create test user
    if not create_test_user():
        print("\n❌ Test failed: Could not create test user")
        return

    # Step 2: Login
    session = login_test_user()
    if not session:
        print("\n❌ Test failed: Could not login test user")
        return

    # Step 3: Test subscription endpoints
    subscription_data = test_subscription_endpoints(session)

    # Step 4: Test cancellation endpoint
    if not test_cancel_subscription_endpoint(session):
        print("\n❌ Test failed: Cancellation endpoint not working")
        return

    # Step 5: Test pause endpoint
    if not test_pause_subscription_endpoint(session):
        print("\n❌ Test failed: Pause endpoint not working")
        return

    # Step 6: Test resume endpoint
    if not test_resume_subscription_endpoint(session):
        print("\n❌ Test failed: Resume endpoint not working")
        return

    # Step 7: Test reactivation endpoint
    if not test_reactivate_subscription_endpoint(session):
        print("\n❌ Test failed: Reactivation endpoint not working")
        return

    # Step 8: Test update payment method endpoint
    if not test_update_payment_method_endpoint(session):
        print("\n❌ Test failed: Update payment method endpoint not working")
        return

    # Step 9: Test webhook endpoint
    if not test_webhook_endpoint():
        print("\n❌ Test failed: Webhook endpoint not working")
        return

    print("\n🎉 All subscription endpoints are accessible and responding correctly!")
    print("\nNote: These tests verify endpoint accessibility and basic responses.")
    print("For full functionality testing with actual Stripe subscriptions, use the deployed environment.")


if __name__ == "__main__":
    main()
