"""
Integration tests for the complete workflow
"""

import json
import tempfile
import os
from unittest.mock import patch
import responses

from make_rule.github_review_comments_fetcher import GitHubReviewCommentsFetcher
from make_rule.bulk_review_comments_fetcher import BulkReviewCommentsFetcher


class TestIntegrationWorkflow:
    """Integration tests for complete workflows"""

    @responses.activate
    def test_full_single_pr_workflow(
        self, mock_github_token, mock_pr_info, mock_reviews, mock_review_comments
    ):
        """Test complete workflow for single PR fetching"""

        # Setup API responses - PR情報
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123",
            json=mock_pr_info,
            status=200,
        )

        # Setup API responses - Reviews（ページネーション対応）
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/reviews",
            json=mock_reviews,
            status=200,
        )

        # 2ページ目は空のレスポンス（ページネーション終了）
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/reviews",
            json=[],
            status=200,
        )

        # Setup API responses - Comments（ページネーション対応）
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=mock_review_comments,
            status=200,
        )

        # 2ページ目は空のレスポンス（ページネーション終了）
        responses.add(
            responses.GET,
            "https://api.github.com/repos/test_owner/test_repo/pulls/123/comments",
            json=[],
            status=200,
        )

        # Execute workflow
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)

        # Get PR info
        pr_info = fetcher.get_pull_request_info("test_owner", "test_repo", 123)
        assert pr_info["number"] == 123

        # Get reviews
        reviews = fetcher.get_pull_request_reviews("test_owner", "test_repo", 123)
        assert len(reviews) == 2

        # Get comments
        comments = fetcher.get_review_comments("test_owner", "test_repo", 123)
        assert len(comments) == 2

        # Format and save data
        result = {
            "pull_request": pr_info,
            "reviews": [fetcher.format_review_info(r) for r in reviews],
            "review_comments": [fetcher.format_comment_info(c) for c in comments],
            "summary": {"total_reviews": len(reviews), "total_comments": len(comments)},
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_filename = f.name

        try:
            fetcher.save_to_json(result, temp_filename)

            # Verify saved data
            with open(temp_filename, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded["pull_request"]["number"] == 123
            assert loaded["summary"]["total_reviews"] == 2
            assert loaded["summary"]["total_comments"] == 2
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    @responses.activate
    @patch("time.sleep")  # Skip delays in tests
    def test_bulk_fetch_workflow(self, mock_sleep, mock_github_token):
        """Test complete workflow for bulk PR fetching"""
        # Setup API responses for 3 PRs
        for pr_num in [1, 2, 3]:
            # PR情報
            responses.add(
                responses.GET,
                f"https://api.github.com/repos/test_owner/test_repo/pulls/{pr_num}",
                json={
                    "number": pr_num,
                    "title": f"PR {pr_num}",
                    "state": "open" if pr_num != 2 else "closed",
                    "user": {"login": f"author{pr_num}"},
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "merged_at": None,
                    "base": {"ref": "main"},
                    "head": {"ref": f"feature-{pr_num}"},
                },
                status=200,
            )

            # Reviews - 1ページ目
            responses.add(
                responses.GET,
                f"https://api.github.com/repos/test_owner/test_repo/pulls/{pr_num}/reviews",
                json=[
                    {
                        "id": pr_num * 1000,
                        "user": {"login": f"reviewer{pr_num}"},
                        "state": "APPROVED",
                        "body": f"Review for PR {pr_num}",
                        "submitted_at": "2024-01-01T10:00:00Z",
                        "commit_id": "abc123",
                    }
                ],
                status=200,
            )

            # Reviews - 2ページ目（空）
            responses.add(
                responses.GET,
                f"https://api.github.com/repos/test_owner/test_repo/pulls/{pr_num}/reviews",
                json=[],
                status=200,
            )

            # Comments - 1ページ目
            responses.add(
                responses.GET,
                f"https://api.github.com/repos/test_owner/test_repo/pulls/{pr_num}/comments",
                json=[
                    {
                        "id": pr_num * 2000,
                        "user": {"login": f"commenter{pr_num}"},
                        "body": f"Comment on PR {pr_num}",
                        "path": f"file{pr_num}.py",
                        "line": pr_num * 10,
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:00:00Z",
                        "commit_id": "abc123",
                        "in_reply_to_id": None,
                        "pull_request_review_id": pr_num * 1000,
                    }
                ],
                status=200,
            )

            # Comments - 2ページ目（空）
            responses.add(
                responses.GET,
                f"https://api.github.com/repos/test_owner/test_repo/pulls/{pr_num}/comments",
                json=[],
                status=200,
            )

        # Execute bulk fetch workflow
        bulk_fetcher = BulkReviewCommentsFetcher(mock_github_token)
        results = bulk_fetcher.fetch_multiple_prs("test_owner", "test_repo", [1, 2, 3])

        # Verify results
        assert len(results) == 3
        assert all(pr_num in results for pr_num in [1, 2, 3])

        # Verify each PR has expected structure
        for pr_num in [1, 2, 3]:
            pr_data = results[pr_num]
            assert "pull_request" in pr_data
            assert "reviews" in pr_data
            assert "review_comments" in pr_data
            assert pr_data["pull_request"]["number"] == pr_num

        # Generate summary
        summary = bulk_fetcher.generate_summary_report(results)
        assert summary["total_prs"] == 3
        assert summary["total_reviews"] == 3
        assert summary["total_comments"] == 3
        assert summary["pr_states"]["open"] == 2
        assert summary["pr_states"]["closed"] == 1

        # Test CSV export
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
            csv_filename = f.name

        try:
            bulk_fetcher.export_to_csv(results, csv_filename)

            # Verify CSV file exists and has content
            assert os.path.exists(csv_filename)
            assert os.path.getsize(csv_filename) > 0

            # Verify CSV content (optional)
            with open(csv_filename, "r", encoding="utf-8") as f:
                content = f.read()
                assert "pr_number" in content  # Check header exists
                assert "1" in content  # Check data exists
        finally:
            if os.path.exists(csv_filename):
                os.unlink(csv_filename)

    def test_error_handling_workflow(self, mock_github_token):
        """Test error handling in the workflow"""
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)

        # Test with network error
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.github.com/repos/test_owner/test_repo/pulls/999",
                status=500,
                json={"message": "Internal Server Error"},
            )

            result = fetcher.get_pull_request_info("test_owner", "test_repo", 999)
            assert result is None

        # Test with authentication error
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.github.com/repos/test_owner/test_repo/pulls/999",
                status=401,
                json={"message": "Bad credentials"},
            )

            result = fetcher.get_pull_request_info("test_owner", "test_repo", 999)
            assert result is None

    def test_data_formatting_consistency(self, mock_github_token, mock_review_comments):
        """Test that data formatting is consistent across methods"""
        fetcher = GitHubReviewCommentsFetcher(mock_github_token)

        # Test comment formatting
        comment = mock_review_comments[0]
        formatted = fetcher.format_comment_info(comment)

        # Verify all expected fields are present
        expected_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
            "body",
            "path",
            "line",
            "commit_id",
            "in_reply_to_id",
            "pull_request_review_id",
        ]

        for field in expected_fields:
            assert field in formatted

        # Verify nested data is properly extracted
        assert formatted["user"] == comment["user"]["login"]
        assert formatted["id"] == comment["id"]
