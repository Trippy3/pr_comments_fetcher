#!/usr/bin/env python3
"""
GitHub APIを使用して複数のプルリクエストのレビューコメントを一括取得するスクリプト
"""

import os
import json
import csv
import argparse
from datetime import datetime
from typing import List, Dict
import time
from .github_review_comments_fetcher import GitHubReviewCommentsFetcher


class BulkReviewCommentsFetcher:
    """複数のプルリクエストのレビューコメントを一括取得するクラス"""

    def __init__(self, token: str):
        """
        初期化

        Args:
            token: GitHub Personal Access Token
        """
        self.fetcher = GitHubReviewCommentsFetcher(token)
        self.token = token

    def fetch_multiple_prs(
        self, owner: str, repo: str, pr_numbers: List[int], delay: float = 1.0
    ) -> Dict[int, Dict]:
        """
        複数のプルリクエストのレビューコメントを取得

        Args:
            owner: リポジトリオーナー
            repo: リポジトリ名
            pr_numbers: プルリクエスト番号のリスト
            delay: リクエスト間の遅延（秒）

        Returns:
            プルリクエスト番号をキーとする辞書
        """
        results = {}

        for i, pr_number in enumerate(pr_numbers):
            print(f"\n[{i + 1}/{len(pr_numbers)}] Fetching PR #{pr_number}...")

            try:
                # プルリクエスト情報の取得
                pr_info = self.fetcher.get_pull_request_info(owner, repo, pr_number)
                if not pr_info:
                    print(f"  Failed to fetch PR #{pr_number}")
                    continue

                # レビューの取得
                reviews = self.fetcher.get_pull_request_reviews(owner, repo, pr_number)
                print(f"  Found {len(reviews)} reviews")

                # レビューコメントの取得
                comments = self.fetcher.get_review_comments(owner, repo, pr_number)
                print(f"  Found {len(comments)} review comments")

                # 結果の保存
                results[pr_number] = {
                    "pull_request": pr_info,
                    "reviews": reviews,
                    "review_comments": comments,
                }

                # レート制限を避けるための遅延
                if i < len(pr_numbers) - 1:
                    time.sleep(delay)

            except Exception as e:
                print(f"  Error processing PR #{pr_number}: {e}")

        return results

    def export_to_csv(self, data: Dict[int, Dict], filename: str):
        """
        データをCSVファイルにエクスポート

        Args:
            data: プルリクエストデータ
            filename: 出力ファイル名
        """
        rows = []

        for pr_number, pr_data in data.items():
            pr_info = pr_data["pull_request"]

            # レビューコメントの処理
            for comment in pr_data["review_comments"]:
                if comment is None:
                    continue
                rows.append(
                    {
                        "pr_number": pr_number,
                        "pr_title": pr_info.get("title"),
                        "pr_state": pr_info.get("state"),
                        "pr_author": pr_info.get("user", {}).get("login")
                        if pr_info.get("user")
                        else "unknown",
                        "comment_id": comment.get("id"),
                        "comment_author": comment.get("user", {}).get("login")
                        if comment.get("user")
                        else "unknown",
                        "comment_body": comment.get("body"),
                        "file_path": comment.get("path"),
                        "line_number": comment.get("line"),
                        "created_at": comment.get("created_at"),
                        "updated_at": comment.get("updated_at"),
                        "in_reply_to": comment.get("in_reply_to_id"),
                    }
                )

        # CSVファイルに書き込み
        if rows:
            fieldnames = list(rows[0].keys())
            with open(filename, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"\nData exported to {filename}")
        else:
            print("\nNo data to export")

    def export_to_markdown(self, data: Dict[int, Dict], filename: str):
        """
        データをMarkdownファイルにエクスポート

        Args:
            data: プルリクエストデータ
            filename: 出力ファイル名
        """
        rows = []

        for pr_number, pr_data in data.items():
            # レビューコメントの処理
            for comment in pr_data["review_comments"]:
                if comment is None:
                    continue
                rows.append(
                    {
                        "pr_number": pr_number,
                        "comment_body": comment.get("body"),
                        "file_path": comment.get("path"),
                    }
                )

        # Markdownファイルに書き込み
        if rows:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("| PR Number | Comment Body | File Path |\n")
                f.write("|-----------|--------------|----------|\n")
                for row in rows:
                    # Markdownテーブル用にパイプをエスケープ
                    comment_body = (row["comment_body"] or "").replace("|", "\\|").replace("\n", "<br>")
                    file_path = (row["file_path"] or "").replace("|", "\\|")
                    f.write(f"| {row['pr_number']} | {comment_body} | {file_path} |\n")
            print(f"\nData exported to {filename}")
        else:
            print("\nNo data to export")

    def generate_summary_report(self, data: Dict[int, Dict]) -> Dict:
        """
        サマリーレポートを生成

        Args:
            data: プルリクエストデータ

        Returns:
            サマリー情報
        """
        summary = {
            "total_prs": len(data),
            "total_reviews": 0,
            "total_comments": 0,
            "review_states": {},
            "top_reviewers": {},
            "top_commenters": {},
            "pr_states": {},
            "files_with_most_comments": {},
        }

        for pr_number, pr_data in data.items():
            pr_info = pr_data["pull_request"]

            # PR状態の集計
            state = pr_info.get("state", "unknown")
            summary["pr_states"][state] = summary["pr_states"].get(state, 0) + 1

            # レビューの集計
            summary["total_reviews"] += len(pr_data["reviews"])
            for review in pr_data["reviews"]:
                if review is None:
                    continue
                # レビュー状態
                review_state = review.get("state", "UNKNOWN")
                summary["review_states"][review_state] = (
                    summary["review_states"].get(review_state, 0) + 1
                )

                # レビュアー
                user_info = review.get("user")
                if user_info is None:
                    reviewer = "unknown"
                else:
                    reviewer = user_info.get("login", "unknown")
                summary["top_reviewers"][reviewer] = (
                    summary["top_reviewers"].get(reviewer, 0) + 1
                )

            # コメントの集計
            summary["total_comments"] += len(pr_data["review_comments"])
            for comment in pr_data["review_comments"]:
                if comment is None:
                    continue
                # コメンター
                user_info = comment.get("user")
                if user_info is None:
                    commenter = "unknown"
                else:
                    commenter = user_info.get("login", "unknown")
                summary["top_commenters"][commenter] = (
                    summary["top_commenters"].get(commenter, 0) + 1
                )

                # ファイル別コメント数
                file_path = comment.get("path", "unknown")
                if file_path:
                    summary["files_with_most_comments"][file_path] = (
                        summary["files_with_most_comments"].get(file_path, 0) + 1
                    )

        # トップレビュアーとコメンターをソート
        summary["top_reviewers"] = dict(
            sorted(summary["top_reviewers"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        )

        summary["top_commenters"] = dict(
            sorted(summary["top_commenters"].items(), key=lambda x: x[1], reverse=True)[
                :10
            ]
        )

        summary["files_with_most_comments"] = dict(
            sorted(
                summary["files_with_most_comments"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        )

        return summary


def parse_pr_numbers(pr_numbers_str: str) -> List[int]:
    """
    PR番号の文字列をパース

    Args:
        pr_numbers_str: PR番号の文字列（例: "1,2,3" または "1-5"）

    Returns:
        PR番号のリスト
    """
    pr_numbers = []

    for part in pr_numbers_str.split(","):
        part = part.strip()
        if "-" in part:
            # 範囲指定（例: "1-5"）
            start, end = map(int, part.split("-"))
            pr_numbers.extend(range(start, end + 1))
        else:
            # 単一の番号
            pr_numbers.append(int(part))

    return sorted(set(pr_numbers))  # 重複を除去してソート


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="GitHub APIを使用して複数のプルリクエストのレビューコメントを一括取得"
    )
    parser.add_argument("owner", help="リポジトリオーナー")
    parser.add_argument("repo", help="リポジトリ名")
    parser.add_argument(
        "pr_numbers", help="PR番号（例: '1,2,3' または '1-5' または '1,3-5,7'）"
    )
    parser.add_argument("--token", help="GitHub Personal Access Token")
    parser.add_argument(
        "--output-json", default="bulk_review_comments.json", help="JSON出力ファイル名"
    )
    parser.add_argument("--output-csv", help="CSV出力ファイル名（オプション）")
    parser.add_argument("--output-md", help="Markdown出力ファイル名（オプション）")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="リクエスト間の遅延（秒）"
    )
    parser.add_argument("--summary", action="store_true", help="サマリーレポートを表示")

    args = parser.parse_args()

    # トークンの取得
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token is required.")
        return

    # PR番号のパース
    try:
        pr_numbers = parse_pr_numbers(args.pr_numbers)
        print(f"Processing {len(pr_numbers)} pull requests: {pr_numbers}")
    except ValueError as e:
        print(f"Error parsing PR numbers: {e}")
        return

    # フェッチャーの初期化
    bulk_fetcher = BulkReviewCommentsFetcher(token)

    # データの取得
    start_time = datetime.now()
    data = bulk_fetcher.fetch_multiple_prs(
        args.owner, args.repo, pr_numbers, delay=args.delay
    )
    end_time = datetime.now()

    print(f"\nFetching completed in {end_time - start_time}")

    # JSONファイルに保存
    output_data = {
        "repository": f"{args.owner}/{args.repo}",
        "pr_numbers": pr_numbers,
        "fetched_at": datetime.now().isoformat(),
        "data": data,
    }

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\nJSON data saved to {args.output_json}")

    # CSVファイルに保存（オプション）
    if args.output_csv:
        bulk_fetcher.export_to_csv(data, args.output_csv)

    # Markdownファイルに保存（オプション）
    if args.output_md:
        bulk_fetcher.export_to_markdown(data, args.output_md)

    # サマリーレポートの表示（オプション）
    if args.summary:
        summary = bulk_fetcher.generate_summary_report(data)

        print("\n" + "=" * 50)
        print("SUMMARY REPORT")
        print("=" * 50)
        print(f"Total Pull Requests: {summary['total_prs']}")
        print(f"Total Reviews: {summary['total_reviews']}")
        print(f"Total Review Comments: {summary['total_comments']}")

        print("\nPR States:")
        for state, count in summary["pr_states"].items():
            print(f"  {state}: {count}")

        print("\nReview States:")
        for state, count in summary["review_states"].items():
            print(f"  {state}: {count}")

        print("\nTop Reviewers:")
        for reviewer, count in list(summary["top_reviewers"].items())[:5]:
            print(f"  {reviewer}: {count} reviews")

        print("\nTop Commenters:")
        for commenter, count in list(summary["top_commenters"].items())[:5]:
            print(f"  {commenter}: {count} comments")

        print("\nFiles with Most Comments:")
        for file_path, count in list(summary["files_with_most_comments"].items())[:5]:
            print(f"  {file_path}: {count} comments")


if __name__ == "__main__":
    main()
