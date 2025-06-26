# GitHub Review Comments Fetcher

GitHub APIを使用して、特定のプルリクエストのレビューコメントを取得するPythonツールです。

## 機能

- プルリクエストの基本情報を取得
- レビュー（APPROVED、CHANGES_REQUESTED、COMMENTEDなど）を取得
- レビューコメント（コード行に対するコメント）を取得
- **issueコメント（PR全体に対するコメント）を取得**
- **スレッド構造分析（親コメント以外の返信コメントを特定）**
- **親コメント以外のコメントのみをフィルタリング**
- 取得したデータをJSON形式で保存
- ページネーションに対応（大量のコメントがある場合も全て取得）
- 複数のプルリクエストを一括取得
- CSV形式でのエクスポート
- サマリーレポートの生成

## インストール

このプロジェクトは[uv](https://github.com/astral-sh/uv)を使用してパッケージを管理しています。

### uvのインストール

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# または pip でインストール
pip install uv
```

### プロジェクトのセットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd make_rule

# 依存関係をインストール
uv sync
```

## 使用方法

### 基本的な使い方

単一のプルリクエストのレビューコメントを取得：

```bash
uv run github-review-fetcher [owner] [repo] [pr_number] --token [your_github_token]
```

複数のプルリクエストを一括取得：

```bash
uv run bulk-review-fetcher [owner] [repo] [pr_numbers] --token [your_github_token]
```

### 環境変数を使用する場合

GitHub Personal Access Tokenを環境変数として設定しておくことで、毎回トークンを指定する必要がなくなります：

```bash
export GITHUB_TOKEN="your_github_token"
uv run github-review-fetcher [owner] [repo] [pr_number]
```

### コマンドラインオプション

#### github-review-fetcher

- `owner`: リポジトリのオーナー（ユーザー名または組織名）
- `repo`: リポジトリ名
- `pr_number`: プルリクエスト番号
- `--token`: GitHub Personal Access Token（オプション、環境変数GITHUB_TOKENでも可）
- `--output`: 出力ファイル名（デフォルト: review_comments.json）

#### bulk-review-fetcher

- `owner`: リポジトリのオーナー
- `repo`: リポジトリ名
- `pr_numbers`: PR番号（例: '1,2,3' または '1-5' または '1,3-5,7'）
- `--token`: GitHub Personal Access Token
- `--output-json`: JSON出力ファイル名（デフォルト: bulk_review_comments.json）
- `--output-csv`: CSV出力ファイル名（オプション）
- `--output-md`: Markdown出力ファイル名（オプション）
- `--delay`: リクエスト間の遅延（秒、デフォルト: 1.0）
- `--summary`: サマリーレポートを表示

### 使用例

```bash
# 例1: microsoft/vscode リポジトリのPR #12345 のレビューコメントを取得
uv run github-review-fetcher microsoft vscode 12345 --token ghp_xxxxxxxxxxxxx

# 例2: 出力ファイル名を指定
uv run github-review-fetcher octocat hello-world 1 --output pr1_reviews.json

# 例3: 複数のPRを一括取得（範囲指定）
uv run bulk-review-fetcher facebook react "30000-30010" --summary

# 例4: CSV出力付きで複数のPRを取得
uv run bulk-review-fetcher microsoft vscode "1,5,10-15" --output-csv comments.csv

# 例5: Markdown出力付きで複数のPRを取得
uv run bulk-review-fetcher microsoft vscode "1,5,10-15" --output-md comments.md

# 例6: 環境変数を使用
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxx"
uv run bulk-review-fetcher torvalds linux "100-110" --summary
```

## GitHub Personal Access Tokenの取得方法

1. GitHubにログイン
2. Settings → Developer settings → Personal access tokens → Tokens (classic)
3. "Generate new token" をクリック
4. 必要なスコープを選択：
   - `repo` (プライベートリポジトリの場合)
   - `public_repo` (パブリックリポジトリのみの場合)
5. トークンを生成してコピー

## 出力形式

### JSON出力

JSONファイルには以下の情報が含まれます：

```json
{
  "pull_request": {
    "number": 12345,
    "title": "プルリクエストのタイトル",
    "state": "open",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "merged_at": null,
    "user": "author_username",
    "base_branch": "main",
    "head_branch": "feature-branch"
  },
  "reviews": [
    {
      "id": 1234567,
      "user": "reviewer_username",
      "state": "APPROVED",
      "body": "LGTM!",
      "submitted_at": "2024-01-01T12:00:00Z",
      "commit_id": "abc123..."
    }
  ],
  "all_comments": [
    {
      "id": 7654321,
      "user": "commenter_username",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z",
      "body": "この行はもっと簡潔に書けます",
      "path": "src/main.py",
      "line": 42,
      "commit_id": "abc123...",
      "in_reply_to_id": null,
      "pull_request_review_id": 1234567,
      "type": "review_comment"
    },
    {
      "id": 8765432,
      "user": "another_user",
      "created_at": "2024-01-01T11:00:00Z",
      "updated_at": "2024-01-01T11:00:00Z",
      "body": "PR全体に対するコメントです",
      "type": "issue_comment"
    }
  ],
  "target_comments": [
    {
      "id": 9876543,
      "user": "replying_user",
      "created_at": "2024-01-01T10:30:00Z",
      "updated_at": "2024-01-01T10:30:00Z",
      "body": "親コメントへの返信です",
      "path": "src/main.py",
      "line": 42,
      "commit_id": "abc123...",
      "in_reply_to_id": 7654321,
      "pull_request_review_id": 1234567,
      "type": "review_comment"
    },
    {
      "id": 8765432,
      "user": "another_user",
      "created_at": "2024-01-01T11:00:00Z",
      "updated_at": "2024-01-01T11:00:00Z",
      "body": "PR全体に対するコメントです",
      "type": "issue_comment"
    }
  ],
  "summary": {
    "total_reviews": 3,
    "total_review_comments": 10,
    "total_issue_comments": 5,
    "total_all_comments": 15,
    "total_target_comments": 8,
    "review_states": {
      "APPROVED": 2,
      "CHANGES_REQUESTED": 1
    }
  },
  "fetched_at": "2024-01-03T09:00:00.123456"
}
```

### 重要なフィールド

- **`all_comments`**: 全てのコメント（レビューコメント + issueコメント）
- **`target_comments`**: **親コメント以外のコメント**
  - `in_reply_to_id`が設定されているレビューコメント（返信コメント）
  - 全てのissueコメント（PR全体コメント）
- **`type`**: コメントの種類（`"review_comment"` または `"issue_comment"`）

### CSV出力（bulk-review-fetcherのみ）

CSV形式では以下のカラムが出力されます：

- pr_number
- pr_title
- pr_state
- pr_author
- comment_id
- comment_author
- comment_body
- file_path
- line_number
- created_at
- updated_at
- in_reply_to

### Markdown出力（bulk-review-fetcherのみ）

Markdown形式では以下の3つのカラムのみテーブル形式で出力されます：

- pr_number: プルリクエスト番号
- comment_body: コメント内容
- file_path: ファイルパス

出力例：
```markdown
| PR Number | Comment Body | File Path |
|-----------|--------------|-----------|
| 123 | コメント内容です | src/main.py |
| 124 | 別のコメント | src/utils.py |
```

注意点：
- Markdownテーブル内のパイプ文字（`|`）は自動的にエスケープされます
- 改行文字は`<br>`タグに変換されます

## 注意事項

- GitHub APIにはレート制限があります（認証済みの場合: 5,000リクエスト/時間）
- 大量のコメントがあるプルリクエストの場合、取得に時間がかかることがあります
- プライベートリポジトリにアクセスする場合は、適切な権限を持つトークンが必要です
- 複数のPRを取得する際は、`--delay`オプションでリクエスト間隔を調整できます

## トラブルシューティング

### エラー: 401 Unauthorized
- トークンが正しいか確認してください
- トークンの有効期限が切れていないか確認してください

### エラー: 404 Not Found
- リポジトリ名、オーナー名、PR番号が正しいか確認してください
- プライベートリポジトリの場合、トークンに適切な権限があるか確認してください

### エラー: 403 Forbidden
- APIレート制限に達している可能性があります
- 1時間待ってから再度実行してください
- または`--delay`オプションでリクエスト間隔を増やしてください

## 開発

### プロジェクト構造

```
make_rule/
├── pyproject.toml          # プロジェクト設定
├── README.md              # このファイル
├── main.py                # エントリーポイント
└── src/
    └── make_rule/
        ├── __init__.py
        ├── github_review_comments_fetcher.py  # 単一PR取得
        └── bulk_review_comments_fetcher.py    # 複数PR一括取得
```

### テストの実行

```bash
# テスト用の依存関係をインストール
uv sync --all-extras

# 全てのテストを実行
uv run pytest

# カバレッジレポート付きでテストを実行
uv run pytest --cov

# 特定のテストファイルのみ実行
uv run pytest src/tests/unit/test_github_review_comments_fetcher.py

# 詳細な出力でテスト実行
uv run pytest -vv

# HTMLカバレッジレポートを生成
uv run pytest --cov --cov-report=html
# htmlcov/index.html でレポートを確認
```

### プロジェクト構造

```
make_rule/
├── pyproject.toml          # プロジェクト設定
├── README.md              # このファイル
├── main.py                # エントリーポイント
├── src/
│   ├── make_rule/
│   │   ├── __init__.py
│   │   ├── github_review_comments_fetcher.py  # 単一PR取得
│   │   └── bulk_review_comments_fetcher.py    # 複数PR一括取得
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py    # pytest設定と共通fixtures
│       └── unit/
│           ├── __init__.py
│           ├── test_github_review_comments_fetcher.py
│           ├── test_bulk_review_comments_fetcher.py
│           └── test_integration.py
└── .gitignore
