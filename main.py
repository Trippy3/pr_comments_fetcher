"""
GitHub Review Comments Fetcherのメインエントリーポイント
"""


def main():
    """メインエントリーポイント"""
    print("GitHub Review Comments Fetcher")
    print("=" * 40)
    print("以下のコマンドが利用可能です：")
    print()
    print("1. 単一のPRを取得:")
    print("   uv run github-review-fetcher [owner] [repo] [pr_number]")
    print()
    print("2. 複数のPRを一括取得:")
    print("   uv run bulk-review-fetcher [owner] [repo] [pr_numbers]")
    print()
    print("詳細はREADME.mdを参照してください。")


if __name__ == "__main__":
    main()
