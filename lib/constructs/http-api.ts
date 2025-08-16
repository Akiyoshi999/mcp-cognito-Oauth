import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

export interface McpCognitoOauthHttpApiProps {
  readonly lambdaFunction: lambda.Function;
}

export class McpCognitoOauthHttpApi extends Construct {
  public readonly httpApi: apigwv2.HttpApi;
  public readonly url: string;

  constructor(scope: Construct, id: string, props: McpCognitoOauthHttpApiProps) {
    super(scope, id);

    this.httpApi = new apigwv2.HttpApi(this, "HttpApi", {
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

    const integration = new integrations.HttpLambdaIntegration(
      "HttpApiIntegration",
      props.lambdaFunction
    );

    this.httpApi.addRoutes({
      path: "/{proxy+}",
      methods: [apigwv2.HttpMethod.ANY],
      integration: integration,
    });

    this.url = this.httpApi.url ?? "";
  }
}