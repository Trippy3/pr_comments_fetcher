"""
pytest configuration and shared fixtures
"""

import pytest


@pytest.fixture
def mock_github_token():
    """Mock GitHub Personal Access Token"""
    return "ghp_test_token_12345"


@pytest.fixture
def mock_pr_info():
    """Mock pull request information"""
    return {
        "number": 123,
        "title": "Test Pull Request",
        "state": "open",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "merged_at": None,
        "user": {"login": "test_author"},
        "base": {"ref": "main"},
        "head": {"ref": "feature-branch"},
    }


@pytest.fixture
def mock_reviews():
    """Mock review data"""
    return [
        {
            "id": 1001,
            "user": {"login": "reviewer1"},
            "state": "APPROVED",
            "body": "LGTM!",
            "submitted_at": "2024-01-01T10:00:00Z",
            "commit_id": "abc123",
        },
        {
            "id": 1002,
            "user": {"login": "reviewer2"},
            "state": "CHANGES_REQUESTED",
            "body": "Please fix the issues",
            "submitted_at": "2024-01-01T11:00:00Z",
            "commit_id": "abc123",
        },
    ]


@pytest.fixture
def mock_review_comments():
    """Mock review comments data"""
    return [
        {
            "id": 2001,
            "user": {"login": "commenter1"},
            "created_at": "2024-01-01T09:00:00Z",
            "updated_at": "2024-01-01T09:00:00Z",
            "body": "This needs improvement",
            "path": "src/main.py",
            "line": 42,
            "commit_id": "abc123",
            "in_reply_to_id": None,
            "pull_request_review_id": 1001,
        },
        {
            "id": 2002,
            "user": {"login": "commenter2"},
            "created_at": "2024-01-01T09:30:00Z",
            "updated_at": "2024-01-01T09:30:00Z",
            "body": "Good catch!",
            "path": "src/utils.py",
            "line": 15,
            "commit_id": "abc123",
            "in_reply_to_id": 2001,
            "pull_request_review_id": 1002,
        },
    ]


@pytest.fixture
def mock_api_responses():
    """Mock GitHub API response URLs and data"""
    return {
        "https://api.github.com/repos/test_owner/test_repo/pulls/123": {
            "json": lambda: mock_pr_info(),
            "status_code": 200,
        },
        "https://api.github.com/repos/test_owner/test_repo/pulls/123/reviews": {
            "json": lambda: mock_reviews(),
            "status_code": 200,
        },
        "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments": {
            "json": lambda: mock_review_comments(),
            "status_code": 200,
        },
    }


@pytest.fixture
def sample_csv_row():
    """Sample CSV row data"""
    return {
        "pr_number": 123,
        "pr_title": "Test Pull Request",
        "pr_state": "open",
        "pr_author": "test_author",
        "comment_id": 2001,
        "comment_author": "commenter1",
        "comment_body": "This needs improvement",
        "file_path": "src/main.py",
        "line_number": 42,
        "created_at": "2024-01-01T09:00:00Z",
        "updated_at": "2024-01-01T09:00:00Z",
        "in_reply_to": None,
    }
