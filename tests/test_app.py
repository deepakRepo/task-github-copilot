import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all(self, client):
        """Test that all activities are returned"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9
        assert "Chess Club" in data
        assert "Basketball Team" in data
    
    def test_activity_contains_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
    
    def test_activity_participants_is_list(self, client):
        """Test that participants is a list"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert isinstance(activity["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_student(self, client):
        """Test successful signup for new student"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_signup_verification(self, client):
        """Test that student is actually added to participants"""
        client.post(
            "/activities/Tennis Club/signup?email=newstudent@mergington.edu"
        )
        
        response = client.get("/activities")
        activity = response.json()["Tennis Club"]
        assert "newstudent@mergington.edu" in activity["participants"]
    
    def test_signup_duplicate_student_fails(self, client):
        """Test that duplicate signup fails"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signup for nonexistent activity fails"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_verification_no_duplicates(self, client):
        """Test that duplicate signup doesn't add student twice"""
        # Try to signup same student twice
        client.post(
            "/activities/Art Studio/signup?email=duplicate@mergington.edu"
        )
        client.post(
            "/activities/Art Studio/signup?email=duplicate@mergington.edu"
        )
        
        response = client.get("/activities")
        activity = response.json()["Art Studio"]
        count = activity["participants"].count("duplicate@mergington.edu")
        assert count == 1


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_student(self, client):
        """Test successful unregistration"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_verification(self, client):
        """Test that student is actually removed from participants"""
        client.delete(
            "/activities/Chess Club/unregister?email=daniel@mergington.edu"
        )
        
        response = client.get("/activities")
        activity = response.json()["Chess Club"]
        assert "daniel@mergington.edu" not in activity["participants"]
    
    def test_unregister_nonexistent_student_fails(self, client):
        """Test that unregistering non-registered student fails"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from nonexistent activity fails"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=test@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_then_unregister_flow(self, client):
        """Test complete signup and unregister flow"""
        # Sign up
        response = client.post(
            "/activities/Debate Team/signup?email=flowtester@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify signup
        response = client.get("/activities")
        activity = response.json()["Debate Team"]
        assert "flowtester@mergington.edu" in activity["participants"]
        original_count = len(activity["participants"])
        
        # Unregister
        response = client.delete(
            "/activities/Debate Team/unregister?email=flowtester@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify unregister
        response = client.get("/activities")
        activity = response.json()["Debate Team"]
        assert "flowtester@mergington.edu" not in activity["participants"]
        assert len(activity["participants"]) == original_count - 1


class TestDuplicateRegistrationBugFix:
    """Tests to ensure duplicate registration bug is fixed"""
    
    def test_cannot_register_twice(self, client):
        """Test that student cannot register twice for same activity"""
        email = "testuser@mergington.edu"
        activity = "Science Club"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response2.status_code == 400
        
        # Verify only one entry exists
        response = client.get("/activities")
        activity_data = response.json()[activity]
        assert activity_data["participants"].count(email) == 1
