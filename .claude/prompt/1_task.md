Bedrock AgentCore の gateway を利用して、Lambda を MCP サーバーのツールとして登録したい。
また、OAuth に準拠するよう Cognito を使用してほしい。
AWS のドキュメントをもとに実装して

-   Lambda, Cognito は CDK で実装すること(AgentCore 以外は全て CDK で実装すること)
-   Bedrock AgentCore は python で構築すること
    -   ソースは sdk-deploy に配置すること
    -   削除コードも実装すること
