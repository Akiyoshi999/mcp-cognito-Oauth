# .envファイルを読み込む
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# デプロイ
deploy:
	cdk deploy --profile $(AWS_PROFILE)

# デプロイの確認
deploy-check:
	cdk diff --profile $(AWS_PROFILE)

# デプロイの削除
destroy:
	cdk destroy --profile $(AWS_PROFILE)

diff:
	cdk diff --profile $(AWS_PROFILE)