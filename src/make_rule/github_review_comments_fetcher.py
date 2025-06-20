#!/usr/bin/env python3
"""
GitHub APIを使用してプルリクエストのレビューコメントを取得するスクリプト
"""

import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
import requests


class GitHubReviewCommentsFetcher:
    """GitHubのプルリクエストレビューコメントを取得するクラス"""

    def __init__(self, token: str):
        """
        初期化

        Args:
            token: GitHub Personal Access Token
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}",
        }

    def get_pull_request_reviews(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict]:
        """
        プルリクエストのレビューを取得

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            pr_number: プルリクエスト番号

        Returns:
            レビューのリスト
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

        reviews = []
        page = 1

        while True:
            response = requests.get(
                url, headers=self.headers, params={"page": page, "per_page": 100}
            )

            if response.status_code != 200:
                print(f"Error fetching reviews: {response.status_code}")
                print(response.json())
                break

            data = response.json()
            if not data:
                break

            reviews.extend(data)
            page += 1

        return reviews

    def get_review_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """
        プルリクエストのレビューコメントを取得

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            pr_number: プルリクエスト番号

        Returns:
            レビューコメントのリスト
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"

        comments = []
        page = 1

        while True:
            response = requests.get(
                url, headers=self.headers, params={"page": page, "per_page": 100}
            )

            if response.status_code != 200:
                print(f"Error fetching comments: {response.status_code}")
                print(response.json())
                break

            data = response.json()
            if not data:
                break

            comments.extend(data)
            page += 1

        return comments

    def get_issue_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """
        プルリクエストのissueコメントを取得（PR全体に対するコメント）

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            pr_number: プルリクエスト番号

        Returns:
            issueコメントのリスト
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"

        comments = []
        page = 1

        while True:
            response = requests.get(
                url, headers=self.headers, params={"page": page, "per_page": 100}
            )

            if response.status_code != 200:
                print(f"Error fetching issue comments: {response.status_code}")
                print(response.json())
                break

            data = response.json()
            if not data:
                break

            comments.extend(data)
            page += 1

        return comments

    def get_pull_request_info(
        self, owner: str, repo: str, pr_number: int
    ) -> Optional[Dict]:
        """
        プルリクエストの基本情報を取得

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            pr_number: プルリクエスト番号

        Returns:
            プルリクエスト情報
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"

        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            print(f"Error fetching PR info: {response.status_code}")
            print(response.json())
            return None

        return response.json()

    def format_comment_info(self, comment: Dict) -> Dict:
        """
        レビューコメント情報を整形

        Args:
            comment: コメントデータ

        Returns:
            整形されたコメント情報
        """
        return {
            "id": comment.get("id"),
            "user": comment.get("user", {}).get("login"),
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "body": comment.get("body"),
            "path": comment.get("path"),
            "line": comment.get("line"),
            "commit_id": comment.get("commit_id"),
            "in_reply_to_id": comment.get("in_reply_to_id"),
            "pull_request_review_id": comment.get("pull_request_review_id"),
            "type": "review_comment",
        }

    def format_issue_comment_info(self, comment: Dict) -> Dict:
        """
        issueコメント情報を整形

        Args:
            comment: コメントデータ

        Returns:
            整形されたコメント情報
        """
        return {
            "id": comment.get("id"),
            "user": comment.get("user", {}).get("login"),
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "body": comment.get("body"),
            "type": "issue_comment",
        }

    def format_review_info(self, review: Dict) -> Dict:
        """
        レビュー情報を整形

        Args:
            review: レビューデータ

        Returns:
            整形されたレビュー情報
        """
        return {
            "id": review.get("id"),
            "user": review.get("user", {}).get("login"),
            "state": review.get("state"),
            "body": review.get("body"),
            "submitted_at": review.get("submitted_at"),
            "commit_id": review.get("commit_id"),
        }

    def save_to_json(self, data: Dict, filename: str):
        """
        データをJSONファイルに保存

        Args:
            data: 保存するデータ
            filename: ファイル名
        """
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Data saved to {filename}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="GitHub APIを使用してプルリクエストのレビューコメントを取得"
    )
    parser.add_argument("owner", help="リポジトリオーナー（ユーザー名または組織名）")
    parser.add_argument("repo", help="リポジトリ名")
    parser.add_argument("pr_number", type=int, help="プルリクエスト番号")
    parser.add_argument(
        "--token",
        help="GitHub Personal Access Token（環境変数GITHUB_TOKENからも取得可能）",
    )
    parser.add_argument(
        "--output",
        default="review_comments.json",
        help="出力ファイル名（デフォルト: review_comments.json）",
    )

    args = parser.parse_args()

    # トークンの取得
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token is required.")
        print(
            "Please provide it via --token option or GITHUB_TOKEN environment variable."
        )
        return

    # フェッチャーの初期化
    fetcher = GitHubReviewCommentsFetcher(token)

    print(f"Fetching data for {args.owner}/{args.repo} PR #{args.pr_number}...")

    # プルリクエスト情報の取得
    pr_info = fetcher.get_pull_request_info(args.owner, args.repo, args.pr_number)
    if not pr_info:
        print("Failed to fetch pull request information.")
        return

    # レビューの取得
    print("Fetching reviews...")
    reviews = fetcher.get_pull_request_reviews(args.owner, args.repo, args.pr_number)
    print(f"Found {len(reviews)} reviews")

    # レビューコメントの取得
    print("Fetching review comments...")
    review_comments = fetcher.get_review_comments(args.owner, args.repo, args.pr_number)
    print(f"Found {len(review_comments)} review comments")

    # issueコメントの取得
    print("Fetching issue comments...")
    issue_comments = fetcher.get_issue_comments(args.owner, args.repo, args.pr_number)
    print(f"Found {len(issue_comments)} issue comments")

    # コメントの整形と統合
    formatted_review_comments = [
        fetcher.format_comment_info(comment) for comment in review_comments
    ]
    formatted_issue_comments = [
        fetcher.format_issue_comment_info(comment) for comment in issue_comments
    ]
    
    # 全てのコメントを統合
    all_comments = formatted_review_comments + formatted_issue_comments
    
    # スレッド構造の分析: 親コメント以外（返信コメント）をフィルタリング
    # review_commentsで in_reply_to_id が設定されているものが返信コメント
    reply_comments = [
        comment for comment in formatted_review_comments
        if comment.get("in_reply_to_id") is not None
    ]
    
    # issue_commentsは基本的に独立したコメントなので、すべて含める
    # ユーザーの要求「親コメント以外」に従って、返信コメント + issue_comments を取得
    target_comments = reply_comments + formatted_issue_comments

    # データの整形
    result = {
        "pull_request": {
            "number": pr_info.get("number"),
            "title": pr_info.get("title"),
            "state": pr_info.get("state"),
            "created_at": pr_info.get("created_at"),
            "updated_at": pr_info.get("updated_at"),
            "merged_at": pr_info.get("merged_at"),
            "user": pr_info.get("user", {}).get("login"),
            "base_branch": pr_info.get("base", {}).get("ref"),
            "head_branch": pr_info.get("head", {}).get("ref"),
        },
        "reviews": [fetcher.format_review_info(review) for review in reviews],
        "all_comments": all_comments,
        "target_comments": target_comments,  # 親コメント以外のコメント
        "summary": {
            "total_reviews": len(reviews),
            "total_review_comments": len(review_comments),
            "total_issue_comments": len(issue_comments),
            "total_all_comments": len(all_comments),
            "total_target_comments": len(target_comments),
            "review_states": {},
        },
        "fetched_at": datetime.now().isoformat(),
    }

    # レビュー状態の集計
    for review in reviews:
        state = review.get("state", "UNKNOWN")
        result["summary"]["review_states"][state] = (
            result["summary"]["review_states"].get(state, 0) + 1
        )

    # 結果の保存
    fetcher.save_to_json(result, args.output)

    # サマリーの表示
    print("\n--- Summary ---")
    print(f"Pull Request: #{pr_info.get('number')} - {pr_info.get('title')}")
    print(f"State: {pr_info.get('state')}")
    print(f"Total Reviews: {len(reviews)}")
    print(f"Total Review Comments: {len(review_comments)}")
    print(f"Total Issue Comments: {len(issue_comments)}")
    print(f"Total All Comments: {len(all_comments)}")
    print(f"Target Comments (non-parent): {len(target_comments)}")
    print("\nComment Breakdown:")
    print(f"  Reply Comments (in review threads): {len(reply_comments)}")
    print(f"  Issue Comments (PR-level): {len(formatted_issue_comments)}")
    print("\nReview States:")
    for state, count in result["summary"]["review_states"].items():
        print(f"  {state}: {count}")
    
    print("\nTarget comments body preview:")
    for i, comment in enumerate(target_comments[:3]):  # 最初の3件のみ表示
        print(f"  {i+1}. [{comment['type']}] {comment['user']}: {comment['body'][:100]}...")
    if len(target_comments) > 3:
        print(f"  ... and {len(target_comments) - 3} more comments")


if __name__ == "__main__":
    main()
