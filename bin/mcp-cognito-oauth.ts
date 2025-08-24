#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { config } from "dotenv";
import { McpCognitoOauthStack } from "../lib/mcp-cognito-oauth-stack";

config();

const app = new cdk.App();
new McpCognitoOauthStack(app, "McpCognitoOauthStack", {
  /* If you don't specify 'env', this stack will be environment-agnostic.
   * Account/Region-dependent features and context lookups will not work,
   * but a single synthesized template can be deployed anywhere. */
  /* Uncomment the next line to specialize this stack for the AWS Account
   * and Region that are implied by the current CLI configuration. */
  env: { region: process.env.AWS_REGION },
  /* Uncomment the next line if you know exactly what Account and Region you
   * want to deploy the stack to. */
  /* For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html */
});
