"""
Unit tests for bulk_review_comments_fetcher module
"""

import csv
import tempfile
import os
from unittest.mock import Mock, patch

from make_rule.bulk_review_comments_fetcher import (
    BulkReviewCommentsFetcher,
    parse_pr_numbers,
    main,
)


class TestParsePRNumbers:
    """Test cases for parse_pr_numbers function"""

    def test_single_number(self):
        """Test parsing single PR number"""
        result = parse_pr_numbers("123")
        assert result == [123]

    def test_multiple_numbers(self):
        """Test parsing multiple comma-separated PR numbers"""
        result = parse_pr_numbers("1,2,3,5")
        assert result == [1, 2, 3, 5]

    def test_range(self):
        """Test parsing PR number range"""
        result = parse_pr_numbers("10-15")
        assert result == [10, 11, 12, 13, 14, 15]

    def test_mixed_format(self):
        """Test parsing mixed format (numbers and ranges)"""
        result = parse_pr_numbers("1,3-5,7,10-12")
        assert result == [1, 3, 4, 5, 7, 10, 11, 12]

    def test_duplicates_removed(self):
        """Test that duplicates are removed"""
        result = parse_pr_numbers("1,2,2,3,1,3-5,4")
        assert result == [1, 2, 3, 4, 5]

    def test_whitespace_handling(self):
        """Test handling of whitespace"""
        result = parse_pr_numbers(" 1 , 2 , 3-5 , 7 ")
        assert result == [1, 2, 3, 4, 5, 7]


class TestBulkReviewCommentsFetcher:
    """Test cases for BulkReviewCommentsFetcher class"""

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_initialization(self, mock_fetcher_class, mock_github_token):
        """Test bulk fetcher initialization"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        assert bulk_fetcher.token == mock_github_token
        assert bulk_fetcher.fetcher == mock_fetcher
        mock_fetcher_class.assert_called_once_with(mock_github_token)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    @patch("time.sleep")
    def test_fetch_multiple_prs_success(
        self,
        mock_sleep,
        mock_fetcher_class,
        mock_github_token,
        mock_pr_info,
        mock_reviews,
        mock_review_comments,
    ):
        """Test successful fetching of multiple PRs"""
        # Setup mock fetcher
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.get_pull_request_info.return_value = mock_pr_info
        mock_fetcher.get_pull_request_reviews.return_value = mock_reviews
        mock_fetcher.get_review_comments.return_value = mock_review_comments

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)
        result = bulk_fetcher.fetch_multiple_prs("owner", "repo", [1, 2, 3], delay=0.5)

        assert len(result) == 3
        assert all(pr_num in result for pr_num in [1, 2, 3])
        assert mock_fetcher.get_pull_request_info.call_count == 3
        assert mock_sleep.call_count == 2  # Called between PRs, not after last one
        mock_sleep.assert_called_with(0.5)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_fetch_multiple_prs_with_failure(
        self, mock_fetcher_class, mock_github_token, capsys
    ):
        """Test fetching multiple PRs with some failures"""
        # Setup mock fetcher
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        # Make the second PR fail
        mock_fetcher.get_pull_request_info.side_effect = [
            {"number": 1, "title": "PR 1"},
            None,  # PR 2 fails
            {"number": 3, "title": "PR 3"},
        ]
        mock_fetcher.get_pull_request_reviews.return_value = []
        mock_fetcher.get_review_comments.return_value = []

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)
        result = bulk_fetcher.fetch_multiple_prs("owner", "repo", [1, 2, 3])

        assert len(result) == 2
        assert 1 in result
        assert 2 not in result
        assert 3 in result

        captured = capsys.readouterr()
        assert "Failed to fetch PR #2" in captured.out

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_export_to_csv(self, mock_fetcher_class, mock_github_token):
        """Test exporting data to CSV"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data
        test_data = {
            123: {
                "pull_request": {
                    "title": "Test PR",
                    "state": "open",
                    "user": {"login": "author"},
                },
                "reviews": [],
                "review_comments": [
                    {
                        "id": 1,
                        "user": {"login": "reviewer"},
                        "body": "Test comment",
                        "path": "test.py",
                        "line": 10,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "in_reply_to_id": None,
                    }
                ],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_filename = f.name

        try:
            bulk_fetcher.export_to_csv(test_data, temp_filename)

            # Read back and verify
            with open(temp_filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["pr_number"] == "123"
            assert rows[0]["comment_body"] == "Test comment"
            assert rows[0]["file_path"] == "test.py"
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_export_to_csv_with_none_comments(
        self, mock_fetcher_class, mock_github_token
    ):
        """Test exporting data to CSV with None comments (should be skipped)"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with None comments
        test_data = {
            123: {
                "pull_request": {
                    "title": "Test PR",
                    "state": "open",
                    "user": {"login": "author"},
                },
                "reviews": [],
                "review_comments": [
                    {
                        "id": 1,
                        "user": {"login": "reviewer"},
                        "body": "Valid comment",
                        "path": "test.py",
                        "line": 10,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "in_reply_to_id": None,
                    },
                    None,  # This should be skipped
                    {
                        "id": 2,
                        "user": {"login": "reviewer2"},
                        "body": "Another valid comment",
                        "path": "test2.py",
                        "line": 20,
                        "created_at": "2024-01-01T01:00:00Z",
                        "updated_at": "2024-01-01T01:00:00Z",
                        "in_reply_to_id": None,
                    },
                ],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_filename = f.name

        try:
            # This should not raise an AttributeError
            bulk_fetcher.export_to_csv(test_data, temp_filename)

            # Read back and verify only valid comments are included
            with open(temp_filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Should only have 2 rows (None comment skipped)
            assert len(rows) == 2
            assert rows[0]["comment_body"] == "Valid comment"
            assert rows[1]["comment_body"] == "Another valid comment"

        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_generate_summary_report(self, mock_fetcher_class, mock_github_token):
        """Test generating summary report"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with multiple PRs
        test_data = {
            1: {
                "pull_request": {"state": "open"},
                "reviews": [
                    {"state": "APPROVED", "user": {"login": "reviewer1"}},
                    {"state": "APPROVED", "user": {"login": "reviewer2"}},
                ],
                "review_comments": [
                    {"user": {"login": "commenter1"}, "path": "file1.py"},
                    {"user": {"login": "commenter1"}, "path": "file1.py"},
                    {"user": {"login": "commenter2"}, "path": "file2.py"},
                ],
            },
            2: {
                "pull_request": {"state": "closed"},
                "reviews": [
                    {"state": "CHANGES_REQUESTED", "user": {"login": "reviewer1"}}
                ],
                "review_comments": [
                    {"user": {"login": "commenter3"}, "path": "file1.py"}
                ],
            },
        }

        summary = bulk_fetcher.generate_summary_report(test_data)

        assert summary["total_prs"] == 2
        assert summary["total_reviews"] == 3
        assert summary["total_comments"] == 4
        assert summary["pr_states"]["open"] == 1
        assert summary["pr_states"]["closed"] == 1
        assert summary["review_states"]["APPROVED"] == 2
        assert summary["review_states"]["CHANGES_REQUESTED"] == 1
        assert summary["top_reviewers"]["reviewer1"] == 2
        assert summary["top_commenters"]["commenter1"] == 2
        assert summary["files_with_most_comments"]["file1.py"] == 3

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_generate_summary_report_with_none_comments(
        self, mock_fetcher_class, mock_github_token
    ):
        """Test generating summary report with None comments (should be skipped)"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with None comments and reviews
        test_data = {
            1: {
                "pull_request": {"state": "open"},
                "reviews": [
                    {"state": "APPROVED", "user": {"login": "reviewer1"}},
                    None,  # This should be skipped
                    {"state": "CHANGES_REQUESTED", "user": {"login": "reviewer2"}},
                ],
                "review_comments": [
                    {"user": {"login": "commenter1"}, "path": "file1.py"},
                    None,  # This should be skipped
                    {"user": {"login": "commenter2"}, "path": "file2.py"},
                    None,  # This should be skipped
                ],
            },
        }

        # This should not raise an AttributeError
        summary = bulk_fetcher.generate_summary_report(test_data)

        assert summary["total_prs"] == 1
        assert summary["total_reviews"] == 3  # Counts all including None
        assert summary["total_comments"] == 4  # Counts all including None
        assert summary["pr_states"]["open"] == 1
        assert summary["review_states"]["APPROVED"] == 1
        assert summary["review_states"]["CHANGES_REQUESTED"] == 1
        assert summary["top_reviewers"]["reviewer1"] == 1
        assert summary["top_reviewers"]["reviewer2"] == 1
        assert summary["top_commenters"]["commenter1"] == 1
        assert summary["top_commenters"]["commenter2"] == 1
        assert summary["files_with_most_comments"]["file1.py"] == 1
        assert summary["files_with_most_comments"]["file2.py"] == 1

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_generate_summary_report_with_none_user_fields(
        self, mock_fetcher_class, mock_github_token
    ):
        """Test generating summary report with None user fields (should handle gracefully)"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with None user fields
        test_data = {
            1: {
                "pull_request": {"state": "open"},
                "reviews": [
                    {"state": "APPROVED", "user": None},  # None user field
                    {"state": "CHANGES_REQUESTED", "user": {"login": "reviewer2"}},
                ],
                "review_comments": [
                    {"user": None, "path": "file1.py"},  # None user field
                    {"user": {"login": "commenter2"}, "path": "file2.py"},
                ],
            },
        }

        # This should not raise an AttributeError
        summary = bulk_fetcher.generate_summary_report(test_data)

        assert summary["total_prs"] == 1
        assert summary["total_reviews"] == 2
        assert summary["total_comments"] == 2
        assert summary["pr_states"]["open"] == 1
        assert summary["review_states"]["APPROVED"] == 1
        assert summary["review_states"]["CHANGES_REQUESTED"] == 1
        assert summary["top_reviewers"]["unknown"] == 1  # None user becomes "unknown"
        assert summary["top_reviewers"]["reviewer2"] == 1
        assert summary["top_commenters"]["unknown"] == 1  # None user becomes "unknown"
        assert summary["top_commenters"]["commenter2"] == 1
        assert summary["files_with_most_comments"]["file1.py"] == 1
        assert summary["files_with_most_comments"]["file2.py"] == 1

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_export_to_csv_with_none_user_fields(
        self, mock_fetcher_class, mock_github_token
    ):
        """Test exporting data to CSV with None user fields (should handle gracefully)"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with None user fields
        test_data = {
            123: {
                "pull_request": {
                    "title": "Test PR",
                    "state": "open",
                    "user": None,  # None user field
                },
                "reviews": [],
                "review_comments": [
                    {
                        "id": 1,
                        "user": None,  # None user field
                        "body": "Test comment",
                        "path": "test.py",
                        "line": 10,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "in_reply_to_id": None,
                    },
                ],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            temp_filename = f.name

        try:
            # This should not raise an AttributeError
            bulk_fetcher.export_to_csv(test_data, temp_filename)

            # Read back and verify
            with open(temp_filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            assert rows[0]["pr_author"] == "unknown"  # None user becomes "unknown"
            assert rows[0]["comment_author"] == "unknown"  # None user becomes "unknown"
            assert rows[0]["comment_body"] == "Test comment"

        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_export_to_markdown(self, mock_fetcher_class, mock_github_token):
        """Test exporting data to Markdown"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data
        test_data = {
            123: {
                "pull_request": {
                    "title": "Test PR",
                    "state": "open",
                    "user": {"login": "author"},
                },
                "reviews": [],
                "review_comments": [
                    {
                        "id": 1,
                        "user": {"login": "reviewer"},
                        "body": "Test comment",
                        "path": "test.py",
                        "line": 10,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "in_reply_to_id": None,
                    },
                    {
                        "id": 2,
                        "user": {"login": "reviewer2"},
                        "body": "Comment with | pipe and\nmultiline",
                        "path": "test2.py",
                        "line": 20,
                        "created_at": "2024-01-01T01:00:00Z",
                        "updated_at": "2024-01-01T01:00:00Z",
                        "in_reply_to_id": None,
                    },
                ],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            temp_filename = f.name

        try:
            bulk_fetcher.export_to_markdown(test_data, temp_filename)

            # Read back and verify
            with open(temp_filename, "r", encoding="utf-8") as f:
                content = f.read()

            assert "| PR Number | Comment Body | File Path |" in content
            assert "|-----------|--------------|----------|" in content
            assert "| 123 | Test comment | test.py |" in content
            assert "| 123 | Comment with \\| pipe and<br>multiline | test2.py |" in content
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_export_to_markdown_with_none_comments(
        self, mock_fetcher_class, mock_github_token
    ):
        """Test exporting data to Markdown with None comments (should be skipped)"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with None comments
        test_data = {
            123: {
                "pull_request": {
                    "title": "Test PR",
                    "state": "open",
                    "user": {"login": "author"},
                },
                "reviews": [],
                "review_comments": [
                    {
                        "id": 1,
                        "user": {"login": "reviewer"},
                        "body": "Valid comment",
                        "path": "test.py",
                        "line": 10,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "in_reply_to_id": None,
                    },
                    None,  # This should be skipped
                ],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            temp_filename = f.name

        try:
            # This should not raise an AttributeError
            bulk_fetcher.export_to_markdown(test_data, temp_filename)

            # Read back and verify only valid comments are included
            with open(temp_filename, "r", encoding="utf-8") as f:
                content = f.read()

            # Should only have 1 data row (None comment skipped)
            lines = content.strip().split('\n')
            data_lines = [line for line in lines if line.startswith('| 123')]
            assert len(data_lines) == 1
            assert "Valid comment" in content

        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @patch("make_rule.bulk_review_comments_fetcher.GitHubReviewCommentsFetcher")
    def test_export_to_markdown_empty_data(
        self, mock_fetcher_class, mock_github_token, capsys
    ):
        """Test exporting empty data to Markdown"""
        mock_fetcher = Mock()
        mock_fetcher_class.return_value = mock_fetcher

        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)

        # Create test data with no comments
        test_data = {}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            temp_filename = f.name

        try:
            bulk_fetcher.export_to_markdown(test_data, temp_filename)

            captured = capsys.readouterr()
            assert "No data to export" in captured.out

            # File should not be created or should be empty
            assert not os.path.exists(temp_filename) or os.path.getsize(temp_filename) == 0

        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


class TestMainFunction:
    """Test cases for the bulk fetcher main function"""

    @patch("sys.argv", ["prog", "owner", "repo", "1-3", "--token", "test_token"])
    @patch("make_rule.bulk_review_comments_fetcher.BulkReviewCommentsFetcher")
    @patch("builtins.open", create=True)
    @patch("json.dump")
    def test_main_basic(self, mock_json_dump, mock_open, mock_bulk_fetcher_class):
        """Test basic main function execution"""
        # Setup mock bulk fetcher
        mock_bulk_fetcher = Mock()
        mock_bulk_fetcher_class.return_value = mock_bulk_fetcher
        mock_bulk_fetcher.fetch_multiple_prs.return_value = {"data": "test"}

        main()

        mock_bulk_fetcher_class.assert_called_once_with("test_token")
        mock_bulk_fetcher.fetch_multiple_prs.assert_called_once_with(
            "owner", "repo", [1, 2, 3], delay=1.0
        )

        # Verify JSON dump was called
        assert mock_json_dump.called

    @patch("sys.argv", ["prog", "owner", "repo", "1,5,10"])
    @patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"})
    @patch("make_rule.bulk_review_comments_fetcher.BulkReviewCommentsFetcher")
    @patch("builtins.open", create=True)
    @patch("json.dump")
    def test_main_with_env_token(
        self, mock_json_dump, mock_open, mock_bulk_fetcher_class
    ):
        """Test main function with environment token"""
        mock_bulk_fetcher = Mock()
        mock_bulk_fetcher_class.return_value = mock_bulk_fetcher
        mock_bulk_fetcher.fetch_multiple_prs.return_value = {}

        main()

        mock_bulk_fetcher_class.assert_called_once_with("env_token")

    @patch(
        "sys.argv",
        ["prog", "owner", "repo", "1-3", "--token", "test_token", "--summary"],
    )
    @patch("make_rule.bulk_review_comments_fetcher.BulkReviewCommentsFetcher")
    @patch("builtins.open", create=True)
    @patch("json.dump")
    def test_main_with_summary(
        self, mock_json_dump, mock_open, mock_bulk_fetcher_class, capsys
    ):
        """Test main function with summary option"""
        mock_bulk_fetcher = Mock()
        mock_bulk_fetcher_class.return_value = mock_bulk_fetcher
        mock_bulk_fetcher.fetch_multiple_prs.return_value = {}
        mock_bulk_fetcher.generate_summary_report.return_value = {
            "total_prs": 3,
            "total_reviews": 5,
            "total_comments": 10,
            "pr_states": {"open": 2, "closed": 1},
            "review_states": {"APPROVED": 3, "CHANGES_REQUESTED": 2},
            "top_reviewers": {"reviewer1": 3},
            "top_commenters": {"commenter1": 5},
            "files_with_most_comments": {"file1.py": 4},
        }

        main()

        mock_bulk_fetcher.generate_summary_report.assert_called_once()

        captured = capsys.readouterr()
        assert "SUMMARY REPORT" in captured.out
        assert "Total Pull Requests: 3" in captured.out
        assert "Total Reviews: 5" in captured.out

    @patch(
        "sys.argv",
        [
            "prog",
            "owner",
            "repo",
            "1-3",
            "--token",
            "test_token",
            "--output-csv",
            "output.csv",
        ],
    )
    @patch("make_rule.bulk_review_comments_fetcher.BulkReviewCommentsFetcher")
    @patch("builtins.open", create=True)
    @patch("json.dump")
    def test_main_with_csv_output(
        self, mock_json_dump, mock_open, mock_bulk_fetcher_class
    ):
        """Test main function with CSV output option"""
        mock_bulk_fetcher = Mock()
        mock_bulk_fetcher_class.return_value = mock_bulk_fetcher
        mock_bulk_fetcher.fetch_multiple_prs.return_value = {"test": "data"}

        main()

        mock_bulk_fetcher.export_to_csv.assert_called_once_with(
            {"test": "data"}, "output.csv"
        )

    @patch(
        "sys.argv",
        [
            "prog",
            "owner",
            "repo",
            "1-3",
            "--token",
            "test_token",
            "--output-md",
            "output.md",
        ],
    )
    @patch("make_rule.bulk_review_comments_fetcher.BulkReviewCommentsFetcher")
    @patch("builtins.open", create=True)
    @patch("json.dump")
    def test_main_with_markdown_output(
        self, mock_json_dump, mock_open, mock_bulk_fetcher_class
    ):
        """Test main function with Markdown output option"""
        mock_bulk_fetcher = Mock()
        mock_bulk_fetcher_class.return_value = mock_bulk_fetcher
        mock_bulk_fetcher.fetch_multiple_prs.return_value = {"test": "data"}

        main()

        mock_bulk_fetcher.export_to_markdown.assert_called_once_with(
            {"test": "data"}, "output.md"
        )

    @patch(
        "sys.argv",
        ["prog", "owner", "repo", "invalid-pr-format", "--token", "test_token"],
    )
    def test_main_with_invalid_pr_numbers(self, capsys):
        """Test main function with invalid PR number format"""
        main()  # pytest.raises()を削除
        captured = capsys.readouterr()
        assert "Error parsing PR numbers:" in captured.out
        assert "invalid literal for int()" in captured.out

    @patch("sys.argv", ["prog", "owner", "repo", "1-3"])
    @patch.dict(os.environ, {}, clear=True)
    def test_main_without_token(self, capsys):
        """Test main function without token"""
        main()

        captured = capsys.readouterr()
        assert "Error: GitHub token is required." in captured.out
