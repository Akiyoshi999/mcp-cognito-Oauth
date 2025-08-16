import * as cdk from "aws-cdk-lib";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { Construct } from "constructs";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";

export class McpCognitoOauthStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const fn = new PythonFunction(this, "McpCognitoOauthFunction", {
      entry: "lambda",
      index: "app.py",
      runtime: cdk.aws_lambda.Runtime.PYTHON_3_12,
      handler: "handler",
      functionName: "mcp-function",
      architecture: cdk.aws_lambda.Architecture.X86_64,
      description: "MCP Server for Cognito OAuth",
    });

    // APIGW
    const httpApi = new apigwv2.HttpApi(this, "McpCognitoOauthHttpApi", {
      corsPreflight: {
        allowOrigins: ["*"],
        allowMethods: [
          apigwv2.CorsHttpMethod.GET,
          apigwv2.CorsHttpMethod.POST,
          apigwv2.CorsHttpMethod.PUT,
          apigwv2.CorsHttpMethod.DELETE,
          apigwv2.CorsHttpMethod.OPTIONS,
        ],
        allowHeaders: ["*"],
      },
    });

    const integ = new integrations.HttpLambdaIntegration(
      "McpCognitoOauthHttpApiIntegration",
      fn
    );
    httpApi.addRoutes({
      path: "/{proxy+}",
      methods: [apigwv2.HttpMethod.ANY],
      integration: integ,
    });

    new cdk.CfnOutput(this, "HttpApiUrl", {
      value: httpApi.url ?? "",
      description: "HTTP API URL",
    });
  }
}
