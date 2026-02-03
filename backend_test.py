import requests
import sys
from datetime import datetime
import json

class DiscordBotDashboardTester:
    def __init__(self, base_url="https://otazka-bot.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = "test_session_1770142950030"  # Provided test token
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Add Authorization header with Bearer token
        if self.session_token:
            test_headers['Authorization'] = f'Bearer {self.session_token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n=== Testing Health Endpoints ===")
        
        # Test root endpoint
        self.run_test("Root API", "GET", "", 200)
        
        # Test health endpoint
        self.run_test("Health Check", "GET", "health", 200)

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n=== Testing Auth Endpoints ===")
        
        # Test /auth/me with provided session token
        success, user_data = self.run_test("Get Current User", "GET", "auth/me", 200)
        
        if success:
            print(f"   User: {user_data.get('name', 'Unknown')} ({user_data.get('email', 'No email')})")
            return user_data
        
        return None

    def test_settings_endpoints(self):
        """Test settings management endpoints"""
        print("\n=== Testing Settings Endpoints ===")
        
        # Test get all settings
        self.run_test("Get All Settings", "GET", "settings", 200)
        
        # Test get specific guild settings
        guild_id = "default"
        success, settings_data = self.run_test(
            f"Get Guild Settings ({guild_id})", 
            "GET", 
            f"settings/{guild_id}", 
            200
        )
        
        # Test update guild settings
        if success:
            update_data = {
                "quiz_time": 90,
                "quiz_rounds": 7,
                "poll_enabled": False,
                "countdown_enabled": True,
                "guild_name": "Test Guild"
            }
            
            self.run_test(
                f"Update Guild Settings ({guild_id})",
                "POST",
                f"settings/{guild_id}",
                200,
                data=update_data
            )
            
            # Test validation - invalid quiz_time
            invalid_data = {"quiz_time": 500}  # Should be 30-300
            self.run_test(
                "Update Settings - Invalid quiz_time",
                "POST",
                f"settings/{guild_id}",
                400,
                data=invalid_data
            )
            
            # Test validation - invalid quiz_rounds
            invalid_data = {"quiz_rounds": 25}  # Should be 1-20
            self.run_test(
                "Update Settings - Invalid quiz_rounds",
                "POST",
                f"settings/{guild_id}",
                400,
                data=invalid_data
            )

    def test_stats_endpoint(self):
        """Test statistics endpoint"""
        print("\n=== Testing Stats Endpoint ===")
        
        success, stats_data = self.run_test("Get Bot Statistics", "GET", "stats", 200)
        
        if success:
            expected_keys = ["total_users", "total_quizzes", "total_polls", "leaderboard"]
            for key in expected_keys:
                if key in stats_data:
                    print(f"   {key}: {stats_data[key]}")
                else:
                    print(f"   ⚠️  Missing key: {key}")

    def test_songs_endpoint(self):
        """Test songs endpoint"""
        print("\n=== Testing Songs Endpoint ===")
        
        success, songs_data = self.run_test("Get Songs List", "GET", "songs", 200)
        
        if success:
            expected_genres = ["rap", "pop", "rock", "classic"]
            for genre in expected_genres:
                if genre in songs_data:
                    song_count = len(songs_data[genre])
                    print(f"   {genre}: {song_count} songs")
                    if song_count > 0:
                        first_song = songs_data[genre][0]
                        print(f"     Example: {first_song.get('artist', 'Unknown')} - {first_song.get('song', 'Unknown')}")
                else:
                    print(f"   ⚠️  Missing genre: {genre}")

    def test_logs_endpoint(self):
        """Test command logs endpoint"""
        print("\n=== Testing Logs Endpoint ===")
        
        # Test default logs
        self.run_test("Get Command Logs", "GET", "logs", 200)
        
        # Test logs with limit
        self.run_test("Get Command Logs (limit=10)", "GET", "logs?limit=10", 200)

    def test_unauthenticated_access(self):
        """Test endpoints without authentication"""
        print("\n=== Testing Unauthenticated Access ===")
        
        # Temporarily remove session token
        original_token = self.session_token
        self.session_token = None
        
        # These should return 401
        endpoints_requiring_auth = [
            "auth/me",
            "settings",
            "settings/default", 
            "stats",
            "songs",
            "logs"
        ]
        
        for endpoint in endpoints_requiring_auth:
            self.run_test(f"Unauthorized - {endpoint}", "GET", endpoint, 401)
        
        # Restore token
        self.session_token = original_token

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Discord Bot Dashboard API Tests")
        print(f"Base URL: {self.base_url}")
        print(f"Session Token: {self.session_token[:20]}...")
        
        # Run test suites
        self.test_health_endpoints()
        self.test_auth_endpoints()
        self.test_settings_endpoints()
        self.test_stats_endpoint()
        self.test_songs_endpoint()
        self.test_logs_endpoint()
        self.test_unauthenticated_access()
        
        # Print summary
        print(f"\n📊 Test Results Summary")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for failure in self.failed_tests:
                if 'error' in failure:
                    print(f"  - {failure['test']}: {failure['error']}")
                else:
                    expected = failure.get('expected', 'unknown')
                    actual = failure.get('actual', 'unknown')
                    print(f"  - {failure['test']}: Expected {expected}, got {actual}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = DiscordBotDashboardTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())