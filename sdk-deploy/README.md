# Bedrock AgentCore Gateway with MCP and Cognito OAuth

このディレクトリには、Amazon Bedrock AgentCore Gateway をModel Context Protocol (MCP) サーバーツールとCognito OAuth認証で管理するPythonスクリプトが含まれています。

## ファイル概要

- `gateway_manager.py` - メインのゲートウェイ管理スクリプト
- `mcp_client.py` - ゲートウェイ機能テスト用のMCPクライアント
- `cleanup.py` - 全リソース対応の包括的クリーンアップスクリプト
- `requirements.txt` - Python依存関係
- `config.example.json` - 設定ファイルの例

## セットアップ

1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

2. AWS認証情報が設定されていることを確認:
```bash
aws configure
# または複数プロファイルを使用する場合:
aws configure --profile your-profile-name
```

3. 最初にCDKスタックをデプロイしてLambdaとCognitoリソースを作成:
```bash
cd ..
npm install
cdk deploy
```

4. 設定例をコピーして実際の値で更新:
```bash
cp config.example.json config.json
```

CDKデプロイメント出力の実際の値で `config.json` を更新してください。

**注意**: `--profile` オプションは任意です。指定しない場合はデフォルトのAWS認証情報が使用されます。

## 使用方法

### 1. ゲートウェイ作成

LambdaターゲットとCognito OAuthを含むBedrock AgentCore Gatewayを作成:

```bash
python gateway_manager.py --action create --config-file config.json --region us-west-2 --profile your-aws-profile
```

これにより以下が実行されます:
- 新しいBedrock AgentCore Gatewayの作成
- CognitoでのOAuth 2.0認証設定
- Lambda関数をターゲットとして追加
- リソースがアクティブになるまで待機

### 2. MCPクライアントテスト

MCPクライアントを使用してゲートウェイをテスト:

```bash
python mcp_client.py \
  --gateway-url "https://your-gateway-id.gateway.bedrock-agentcore.us-west-2.amazonaws.com" \
  --client-id "your-cognito-client-id" \
  --client-secret "your-cognito-client-secret" \
  --cognito-domain "your-cognito-domain.auth.us-west-2.amazoncognito.com" \
  --profile your-aws-profile \
  --demo
```

### 3. リソース一覧

全ゲートウェイを一覧表示:

```bash
python gateway_manager.py --action list --region us-west-2 --profile your-aws-profile
```

ゲートウェイ情報を取得:

```bash
python gateway_manager.py --action info --gateway-id your-gateway-id --region us-west-2 --profile your-aws-profile
```

MCP関連リソースを全て一覧表示:

```bash
python cleanup.py --action list --region us-west-2 --profile your-aws-profile
```

### 4. クリーンアップ

ゲートウェイのみクリーンアップ:

```bash
python cleanup.py --action cleanup-gateways --region us-west-2 --profile your-aws-profile
```

全リソースクリーンアップ（CloudFormationスタック含む）:

```bash
python cleanup.py --action cleanup-all --region us-west-2 --profile your-aws-profile
```

確認プロンプトなしで強制クリーンアップ:

```bash
python cleanup.py --action cleanup-all --region us-west-2 --profile your-aws-profile --force
```

## アーキテクチャ

実装により以下が作成されます:

1. **Cognito User Pool** - OAuth 2.0 client credentials flow付き
2. **Lambda Function** - 各種AWSサービス用のMCPツール
3. **Bedrock AgentCore Gateway** - MCPクライアントとLambdaを橋渡し
4. **OAuth認証** - ツールへの安全なアクセス

## 利用可能なMCPツール

Lambda関数は以下のMCPツールを提供:

- `generate_uuid` - ランダムUUID生成
- `get_system_info` - Lambdaと環境情報取得
- `store_data` - S3にデータ保存
- `retrieve_data` - S3からデータ取得
- `process_text_with_bedrock` - Bedrockモデルでテキスト処理
- `validate_oauth_token` - Cognito OAuthトークン検証

## 認証フロー

1. クライアントがclient credentialsを使用してCognitoで認証
2. OAuthアクセストークンを受信
3. MCPリクエストのAuthorizationヘッダーにトークンを含める
4. ゲートウェイがトークンを検証してLambdaにリクエスト転送
5. LambdaがMCPツールを実行して結果を返却

## エラーハンドリング

全スクリプトには包括的なエラーハンドリングとログ出力が含まれています。操作が失敗した場合は、詳細なエラー情報についてログを確認してください。

## セキュリティノート

- クライアントシークレットは安全に保存してください（例：AWS Secrets Manager）
- OAuthスコープにより特定操作へのアクセスを制限
- Lambda関数は必要最小限のIAM権限を持つ
- 全通信でHTTPS/TLS暗号化を使用

## トラブルシューティング

1. **ゲートウェイ作成失敗**: Bedrock AgentCoreのIAM権限を確認
2. **OAuth認証失敗**: クライアントID/シークレットとドメインを確認
3. **MCP呼び出し失敗**: Lambda関数の権限とログを確認
4. **タイムアウトエラー**: gateway_manager.pyの待機時間を増加

詳細ログを有効にするには:

```python
logging.basicConfig(level=logging.DEBUG)
```