"""
Unit tests for github_review_comments_fetcher module
"""

import json
import tempfile
import os
from unittest.mock import Mock, patch
import responses

from make_rule.github_review_comments_fetcher import GitHubReviewCommentsFetcher, main


class TestGitHubReviewCommentsFetcher:
    """Test cases for GitHubReviewCommentsFetcher class"""

    def test_initialization(self, mock_github_token):
        """Test fetcher initialization"""
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)

        assert fetcher.token == mock_github_token
        assert fetcher.base_url == "https://api.github.com"
        assert fetcher.headers["Authorization"] == f"token {mock_github_token}"
        assert fetcher.headers["Accept"] == "application/vnd.github.v3+json"

    @responses.activate
    def test_get_pull_request_info_success(self, mock_github_token, mock_pr_info):
        """Test successful PR info retrieval"""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123",
            json=mock_pr_info,
            status=200,
        )

        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        result = fetcher.get_pull_request_info("test_owner", "test_repo", 123)

        assert result == mock_pr_info
        assert result["number"] == 123
        assert result["title"] == "Test Pull Request"

    @responses.activate
    def test_get_pull_request_info_failure(self, mock_github_token, capsys):
        """Test PR info retrieval failure"""
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123",
            json={"message": "Not Found"},
            status=404,
        )

        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        result = fetcher.get_pull_request_info("test_owner", "test_repo", 123)

        assert result is None
        captured = capsys.readouterr()
        assert "Error fetching PR info: 404" in captured.out

    @responses.activate
    def test_get_pull_request_reviews(self, mock_github_token, mock_reviews):
        """Test retrieving PR reviews"""
        # First page with data
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/reviews",
            json=mock_reviews,
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "1", "per_page": "100"})
            ],
        )
        # Second page empty
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/reviews",
            json=[],
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "2", "per_page": "100"})
            ],
        )

        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        result = fetcher.get_pull_request_reviews("test_owner", "test_repo", 123)

        assert len(result) == 2
        assert result[0]["state"] == "APPROVED"
        assert result[1]["state"] == "CHANGES_REQUESTED"

    @responses.activate
    def test_get_review_comments(self, mock_github_token, mock_review_comments):
        """Test retrieving review comments"""
        # First page with data
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=mock_review_comments,
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "1", "per_page": "100"})
            ],
        )
        # Second page empty
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=[],
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "2", "per_page": "100"})
            ],
        )

        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        result = fetcher.get_review_comments("test_owner", "test_repo", 123)

        assert len(result) == 2
        assert result[0]["path"] == "src/main.py"
        assert result[1]["path"] == "src/utils.py"

    def test_format_comment_info(self, mock_github_token, mock_review_comments):
        """Test comment info formatting"""
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        comment = mock_review_comments[0]
        formatted = fetcher.format_comment_info(comment)

        assert formatted["id"] == comment["id"]
        assert formatted["user"] == "commenter1"
        assert formatted["body"] == comment["body"]
        assert formatted["path"] == comment["path"]
        assert formatted["line"] == comment["line"]

    def test_format_review_info(self, mock_github_token, mock_reviews):
        """Test review info formatting"""
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        review = mock_reviews[0]
        formatted = fetcher.format_review_info(review)

        assert formatted["id"] == review["id"]
        assert formatted["user"] == "reviewer1"
        assert formatted["state"] == "APPROVED"
        assert formatted["body"] == review["body"]

    def test_save_to_json(self, mock_github_token):
        """Test saving data to JSON file"""
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        test_data = {"test": "data", "number": 123}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_filename = f.name

        try:
            fetcher.save_to_json(test_data, temp_filename)

            # Read back and verify
            with open(temp_filename, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @responses.activate
    def test_pagination_handling(self, mock_github_token):
        """Test pagination handling for large result sets"""
        # Create mock data for 3 pages
        page1_data = [{"id": i, "body": f"Comment {i}"} for i in range(100)]
        page2_data = [{"id": i, "body": f"Comment {i}"} for i in range(100, 200)]
        page3_data = [{"id": i, "body": f"Comment {i}"} for i in range(200, 250)]

        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=page1_data,
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "1", "per_page": "100"})
            ],
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=page2_data,
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "2", "per_page": "100"})
            ],
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=page3_data,
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "3", "per_page": "100"})
            ],
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=[],
            status=200,
            match=[
                responses.matchers.query_param_matcher({"page": "4", "per_page": "100"})
            ],
        )

        fetcher = GitHubReviewCommentsFetcher(mock_github_token)
        result = fetcher.get_review_comments("test_owner", "test_repo", 123)

        assert len(result) == 250
        assert result[0]["id"] == 0
        assert result[249]["id"] == 249


class TestMainFunction:
    """Test cases for the main function"""

    @patch("sys.argv", ["prog", "owner", "repo", "123", "--token", "test_token"])
    @patch("make_rule.github_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_main_with_token_arg(
        self, mock_fetcher_class, mock_pr_info, mock_reviews, mock_review_comments
    ):
        """Test main function with token as argument"""
        # Setup mock fetcher instance
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_pull_request_info.return_value = mock_pr_info
        mock_fetcher.get_pull_request_reviews.return_value = mock_reviews
        mock_fetcher.get_review_comments.return_value = mock_review_comments
        mock_fetcher.get_issue_comments.return_value = []

        # Mock format methods to return formatted data
        mock_fetcher.format_comment_info.side_effect = lambda comment: {
            **comment,
            "type": "review_comment",
        }
        mock_fetcher.format_issue_comment_info.side_effect = lambda comment: {
            **comment,
            "type": "issue_comment",
        }
        mock_fetcher.format_review_info.side_effect = lambda review: review

        main()

        mock_fetcher_class.assert_called_once_with("test_token")
        mock_fetcher.get_pull_request_info.assert_called_once_with("owner", "repo", 123)
        mock_fetcher.save_to_json.assert_called_once()

    @patch("sys.argv", ["prog", "owner", "repo", "123"])
    @patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"})
    @patch("make_rule.github_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_main_with_env_token(
        self, mock_fetcher_class, mock_pr_info, mock_reviews, mock_review_comments
    ):
        """Test main function with token from environment"""
        # Setup mock fetcher instance
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_pull_request_info.return_value = mock_pr_info
        mock_fetcher.get_pull_request_reviews.return_value = mock_reviews
        mock_fetcher.get_review_comments.return_value = mock_review_comments
        mock_fetcher.get_issue_comments.return_value = []

        # Mock format methods to return formatted data
        mock_fetcher.format_comment_info.side_effect = lambda comment: {
            **comment,
            "type": "review_comment",
        }
        mock_fetcher.format_issue_comment_info.side_effect = lambda comment: {
            **comment,
            "type": "issue_comment",
        }
        mock_fetcher.format_review_info.side_effect = lambda review: review

        main()

        mock_fetcher_class.assert_called_once_with("env_token")

    @patch("sys.argv", ["prog", "owner", "repo", "123"])
    @patch.dict(os.environ, {}, clear=True)
    def test_main_without_token(self, capsys):
        """Test main function without token"""
        main()

        captured = capsys.readouterr()
        assert "Error: GitHub token is required." in captured.out

    @patch(
        "sys.argv",
        [
            "prog",
            "owner",
            "repo",
            "123",
            "--token",
            "test_token",
            "--output",
            "custom.json",
        ],
    )
    @patch("make_rule.github_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_main_with_custom_output(
        self, mock_fetcher_class, mock_pr_info, mock_reviews, mock_review_comments
    ):
        """Test main function with custom output filename"""
        # Setup mock fetcher instance
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_pull_request_info.return_value = mock_pr_info
        mock_fetcher.get_pull_request_reviews.return_value = mock_reviews
        mock_fetcher.get_review_comments.return_value = mock_review_comments
        mock_fetcher.get_issue_comments.return_value = []

        # Mock format methods to return formatted data
        mock_fetcher.format_comment_info.side_effect = lambda comment: {
            **comment,
            "type": "review_comment",
        }
        mock_fetcher.format_issue_comment_info.side_effect = lambda comment: {
            **comment,
            "type": "issue_comment",
        }
        mock_fetcher.format_review_info.side_effect = lambda review: review

        main()

        # Check that save_to_json was called with custom filename
        save_call_args = mock_fetcher.save_to_json.call_args
        assert save_call_args[0][1] == "custom.json"

    @patch("sys.argv", ["prog", "owner", "repo", "123", "--token", "test_token"])
    @patch("make_rule.github_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_main_pr_not_found(self, mock_fetcher_class, capsys):
        """Test main function when PR is not found"""
        # Setup mock fetcher instance
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_pull_request_info.return_value = None

        main()

        captured = capsys.readouterr()
        assert "Failed to fetch pull request information." in captured.out
