import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import { McpCognitoOauthFunction } from "./constructs/lambda-function";
import { McpCognitoOauthHttpApi } from "./constructs/http-api";
import { McpCognito } from "./constructs/cognito";

interface McpCognitoOauthStackProps extends cdk.StackProps {
  readonly functionTimeout?: cdk.Duration;
  readonly logRetention?: logs.RetentionDays;
}

export class McpCognitoOauthStack extends cdk.Stack {
  public readonly httpApiUrl: string;
  public readonly lambdaFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: McpCognitoOauthStackProps) {
    super(scope, id, props);

    // const cognitoConstruct = new McpCognito(this, "McpCognito", {});

    const lambdaConstruct = new McpCognitoOauthFunction(
      this,
      "McpCognitoOauthFunction",
      {
        functionTimeout: props?.functionTimeout,
        logRetention: props?.logRetention,
        // cognitoUserPoolId: cognitoConstruct.userPool.userPoolId,
      }
    );
    this.lambdaFunction = lambdaConstruct.function;

    const httpApiConstruct = new McpCognitoOauthHttpApi(
      this,
      "McpCognitoOauthHttpApi",
      {
        lambdaFunction: this.lambdaFunction,
      }
    );
    this.httpApiUrl = httpApiConstruct.url;

    new cdk.CfnOutput(this, "HttpApiUrl", {
      value: this.httpApiUrl,
      description: "HTTP API URL for MCP Cognito OAuth",
      exportName: `${this.stackName}-HttpApiUrl`,
    });

    new cdk.CfnOutput(this, "LambdaFunctionArn", {
      value: this.lambdaFunction.functionArn,
      description: "Lambda Function ARN",
      exportName: `${this.stackName}-LambdaFunctionArn`,
    });
  }
}
