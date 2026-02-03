import requests
import sys
import json
from datetime import datetime

class QuizBotAPITester:
    def __init__(self, base_url="https://otazka-bot.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_user_id = None
        self.test_username = f"test_user_{datetime.now().strftime('%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_create_user(self):
        """Test user creation"""
        success, response = self.run_test(
            "Create User",
            "POST",
            "users",
            200,
            data={"username": self.test_username}
        )
        if success and 'id' in response:
            self.test_user_id = response['id']
            print(f"   Created user ID: {self.test_user_id}")
            return True
        return False

    def test_get_user(self):
        """Test get user by ID"""
        if not self.test_user_id:
            print("❌ No user ID available for testing")
            return False
        
        return self.run_test(
            "Get User by ID",
            "GET",
            f"users/{self.test_user_id}",
            200
        )[0]

    def test_get_user_by_username(self):
        """Test get user by username"""
        return self.run_test(
            "Get User by Username",
            "GET",
            f"users/by-username/{self.test_username}",
            200
        )[0]

    def test_generate_quiz_question(self):
        """Test quiz question generation"""
        success, response = self.run_test(
            "Generate Quiz Question",
            "POST",
            "questions/generate",
            200,
            data={"difficulty": "medium", "question_type": "quiz"}
        )
        if success and 'id' in response:
            self.question_id = response['id']
            return True
        return False

    def test_generate_math_calc_question(self):
        """Test math calculation question generation"""
        return self.run_test(
            "Generate Math Calc Question",
            "POST",
            "questions/generate",
            200,
            data={"difficulty": "easy", "question_type": "math_calc"}
        )[0]

    def test_generate_math_equation_question(self):
        """Test math equation question generation"""
        return self.run_test(
            "Generate Math Equation Question",
            "POST",
            "questions/generate",
            200,
            data={"difficulty": "medium", "question_type": "math_equation"}
        )[0]

    def test_generate_math_puzzle_question(self):
        """Test math puzzle question generation"""
        return self.run_test(
            "Generate Math Puzzle Question",
            "POST",
            "questions/generate",
            200,
            data={"difficulty": "hard", "question_type": "math_puzzle"}
        )[0]

    def test_generate_ai_question(self):
        """Test AI question generation"""
        success, response = self.run_test(
            "Generate AI Question",
            "POST",
            "questions/generate-ai",
            200,
            data={"difficulty": "medium", "question_type": "quiz"}
        )
        return success

    def test_submit_answer(self):
        """Test answer submission"""
        if not hasattr(self, 'question_id') or not self.test_user_id:
            print("❌ No question ID or user ID available for answer submission")
            return False
        
        success, response = self.run_test(
            "Submit Answer",
            "POST",
            "questions/answer",
            200,
            data={
                "question_id": self.question_id,
                "user_id": self.test_user_id,
                "selected_answer": "test_answer",
                "time_taken": 5.0
            }
        )
        
        if success and 'mee6_command' in response:
            print(f"   Mee6 Command: {response.get('mee6_command', 'None')}")
        
        return success

    def test_leaderboard(self):
        """Test leaderboard endpoint"""
        return self.run_test(
            "Get Leaderboard",
            "GET",
            "leaderboard",
            200,
            params={"limit": 10}
        )[0]

    def test_start_session(self):
        """Test game session start"""
        if not self.test_user_id:
            print("❌ No user ID available for session testing")
            return False
        
        success, response = self.run_test(
            "Start Game Session",
            "POST",
            f"sessions/start?user_id={self.test_user_id}&game_type=quiz",
            200
        )
        
        if success and 'session_id' in response:
            self.session_id = response['session_id']
            return True
        return False

    def test_end_session(self):
        """Test game session end"""
        if not hasattr(self, 'session_id'):
            print("❌ No session ID available for ending session")
            return False
        
        return self.run_test(
            "End Game Session",
            "POST",
            f"sessions/{self.session_id}/end?score=100&correct=5&total=10",
            200
        )[0]

def main():
    print("🚀 Starting Quiz Bot API Tests...")
    print("=" * 50)
    
    tester = QuizBotAPITester()
    
    # Test sequence
    tests = [
        tester.test_root_endpoint,
        tester.test_create_user,
        tester.test_get_user,
        tester.test_get_user_by_username,
        tester.test_generate_quiz_question,
        tester.test_generate_math_calc_question,
        tester.test_generate_math_equation_question,
        tester.test_generate_math_puzzle_question,
        tester.test_generate_ai_question,
        tester.test_submit_answer,
        tester.test_leaderboard,
        tester.test_start_session,
        tester.test_end_session,
    ]
    
    # Run all tests
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {str(e)}")
    
    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())