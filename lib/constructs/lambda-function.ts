import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";

export interface McpCognitoOauthFunctionProps {
  readonly functionTimeout?: cdk.Duration;
  readonly logRetention?: logs.RetentionDays;
}

export class McpCognitoOauthFunction extends Construct {
  public readonly function: lambda.Function;

  constructor(scope: Construct, id: string, props?: McpCognitoOauthFunctionProps) {
    super(scope, id);

    const functionTimeout = props?.functionTimeout ?? cdk.Duration.seconds(30);
    const logRetention = props?.logRetention ?? logs.RetentionDays.ONE_DAY;

    this.function = new PythonFunction(this, "Function", {
      entry: "lambda",
      index: "app.py",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler",
      architecture: lambda.Architecture.X86_64,
      description: "MCP Server for Cognito OAuth",
      timeout: functionTimeout,
      logRetention: logRetention,
    });
  }
}