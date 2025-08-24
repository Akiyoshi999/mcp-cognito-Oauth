import * as cognito from "aws-cdk-lib/aws-cognito";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";

export interface McpCognitoProps {
  readonly userPoolName?: string;
  readonly domainPrefix?: string;
  readonly clientName?: string;
}

export class McpCognito extends Construct {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolDomain: cognito.UserPoolDomain;
  public readonly userPoolClient: cognito.UserPoolClient; // For machine-to-machine
  public readonly inspectorClient: cognito.UserPoolClient; // For MCP Inspector
  public readonly resourceServer: cognito.UserPoolResourceServer;

  constructor(scope: Construct, id: string, props: McpCognitoProps) {
    super(scope, id);

    this.userPool = new cognito.UserPool(this, "UserPool", {
      userPoolName: props.userPoolName ?? "mcp_bedrock_agentcore_user_pool",
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    this.userPoolDomain = new cognito.UserPoolDomain(this, "UserPoolDomain", {
      userPool: this.userPool,
      cognitoDomain: {
        domainPrefix: props.domainPrefix ?? "mcp-bedrock-auth",
      },
    });

    // Create resource server for OAuth scopes
    const readScope = new cognito.ResourceServerScope({
      scopeName: "read",
      scopeDescription: "Read access to MCP tools",
    });
    const writeScope = new cognito.ResourceServerScope({
      scopeName: "write", 
      scopeDescription: "Write access to MCP tools",
    });
    const executeScope = new cognito.ResourceServerScope({
      scopeName: "execute",
      scopeDescription: "Execute MCP tools",
    });

    this.resourceServer = new cognito.UserPoolResourceServer(this, "ResourceServer", {
      userPool: this.userPool,
      identifier: "mcp-tools",
      scopes: [readScope, writeScope, executeScope],
    });

    // Create app client for machine-to-machine authentication
    this.userPoolClient = new cognito.UserPoolClient(this, "M2MClient", {
      userPool: this.userPool,
      userPoolClientName: props.clientName ?? "mcp-bedrock-agentcore-client",
      generateSecret: true,
      oAuth: {
        flows: {
          clientCredentials: true,
        },
        scopes: [
          cognito.OAuthScope.resourceServer(this.resourceServer, readScope),
          cognito.OAuthScope.resourceServer(this.resourceServer, writeScope),
          cognito.OAuthScope.resourceServer(this.resourceServer, executeScope),
        ],
      },
    });

    // Create separate client for MCP Inspector (authorization code flow)
    this.inspectorClient = new cognito.UserPoolClient(this, "InspectorClient", {
      userPool: this.userPool,
      userPoolClientName: "mcp-inspector-client",
      generateSecret: false, // Public client for PKCE flow
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.resourceServer(this.resourceServer, readScope),
          cognito.OAuthScope.resourceServer(this.resourceServer, writeScope),
          cognito.OAuthScope.resourceServer(this.resourceServer, executeScope),
        ],
        callbackUrls: [
          "http://localhost:6274/oauth/callback/debug", // MCP Inspector callback
          "https://localhost:6274/oauth/callback/debug", // HTTPS variant
        ],
        logoutUrls: [
          "http://localhost:6274/logout",
          "https://localhost:6274/logout",
        ],
      },
      supportedIdentityProviders: [cognito.UserPoolClientIdentityProvider.COGNITO],
    });

    // Outputs for easy access
    new cdk.CfnOutput(this, "UserPoolId", {
      value: this.userPool.userPoolId,
      description: "Cognito User Pool ID",
      exportName: `${cdk.Stack.of(this).stackName}-UserPoolId`,
    });

    new cdk.CfnOutput(this, "UserPoolClientId", {
      value: this.userPoolClient.userPoolClientId,
      description: "Cognito User Pool Client ID (Machine-to-Machine)",
      exportName: `${cdk.Stack.of(this).stackName}-UserPoolClientId`,
    });

    new cdk.CfnOutput(this, "InspectorClientId", {
      value: this.inspectorClient.userPoolClientId,
      description: "Cognito User Pool Client ID (MCP Inspector)",
      exportName: `${cdk.Stack.of(this).stackName}-InspectorClientId`,
    });

    new cdk.CfnOutput(this, "CognitoDomain", {
      value: this.userPoolDomain.domainName,
      description: "Cognito Domain for OAuth",
      exportName: `${cdk.Stack.of(this).stackName}-CognitoDomain`,
    });

    new cdk.CfnOutput(this, "CognitoDiscoveryUrl", {
      value: `https://cognito-idp.${cdk.Stack.of(this).region}.amazonaws.com/${this.userPool.userPoolId}/.well-known/openid-configuration`,
      description: "OpenID Connect Discovery URL for Gateway configuration",
      exportName: `${cdk.Stack.of(this).stackName}-DiscoveryUrl`,
    });

    new cdk.CfnOutput(this, "AuthorizationUrl", {
      value: `https://${this.userPoolDomain.domainName}.auth.${cdk.Stack.of(this).region}.amazoncognito.com/oauth2/authorize`,
      description: "Authorization URL for OAuth flow",
      exportName: `${cdk.Stack.of(this).stackName}-AuthorizationUrl`,
    });

    new cdk.CfnOutput(this, "TokenUrl", {
      value: `https://${this.userPoolDomain.domainName}.auth.${cdk.Stack.of(this).region}.amazoncognito.com/oauth2/token`,
      description: "Token URL for OAuth flow",
      exportName: `${cdk.Stack.of(this).stackName}-TokenUrl`,
    });
  }
}