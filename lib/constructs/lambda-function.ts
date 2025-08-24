import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";

export interface McpCognitoOauthFunctionProps {
  readonly functionTimeout?: cdk.Duration;
  readonly logRetention?: logs.RetentionDays;
  readonly cognitoUserPoolId?: string;
}

export class McpCognitoOauthFunction extends Construct {
  public readonly function: lambda.Function;
  public readonly genUuidFunction: lambda.Function;

  constructor(
    scope: Construct,
    id: string,
    props?: McpCognitoOauthFunctionProps
  ) {
    super(scope, id);

    const functionTimeout = props?.functionTimeout ?? cdk.Duration.seconds(30);
    const logRetention = props?.logRetention ?? logs.RetentionDays.ONE_DAY;

    this.function = new PythonFunction(this, "Function", {
      entry: "lambda/awslabs-mcp",
      index: "app.py",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler",
      architecture: lambda.Architecture.X86_64,
      description: "MCP Tools for Bedrock AgentCore Gateway",
      timeout: functionTimeout,
      logRetention: logRetention,
      environment: {
        COGNITO_USER_POOL_ID: props?.cognitoUserPoolId ?? "",
      },
    });

    this.genUuidFunction = new PythonFunction(this, "GenUuidFunction", {
      entry: "lambda/gen-uuid",
      index: "app.py",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler",
      architecture: lambda.Architecture.X86_64,
    });

    // Add permissions for Bedrock and other AWS services
    this.function.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["lambda:InvokeFunction"],
        resources: ["*"],
      })
    );

    // Output the function ARN for Gateway target configuration
    new cdk.CfnOutput(this, "McpLambdaFunctionArn", {
      value: this.function.functionArn,
      description: "Lambda Function ARN for MCP tools",
      exportName: `${cdk.Stack.of(this).stackName}-McpLambdaFunctionArn`,
    });

    new cdk.CfnOutput(this, "GenUuidFunctionArn", {
      value: this.genUuidFunction.functionArn,
      description: "Lambda Function ARN for GenUuid",
      exportName: `${cdk.Stack.of(this).stackName}-GenUuidFunctionArn`,
    });
  }
}
