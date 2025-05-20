# Set up Authentication in Azure Container App

This document provides step-by-step instructions to configure Azure App Registrations for a front-end and back-end application.

## Prerequisites

- Access to **Microsoft Entra ID**
- Necessary permissions to create and manage **App Registrations**

## Step 1: Add Authentication Provider

We will add Microsoft Entra ID as an authentication provider to API and Web Application.

1. Add Authentication Provider in Web Application

   - Go to deployed Container App and select `ca-cps-<randomname>-web` and click **Add Identity Provider** button in Authentication.  
     ![add_auth_provider_web_1](./images/add_auth_provider_web_1.png)

   - Select **Microsoft** and set **Client secret expiration**, then click **Add** button.  
     ![add_auth_provider_web_2](./images/add_auth_provider_web_2.png)

    - Set **Unauthenticated requests**, then click **Add** button.  
     ![add_auth_provider_api_3](./images/add_auth_provider_web_4.png)

> **Note:** If you encounter the following error message indicating that your organization's policy prohibits the automatic use of secrets, please refer to our [Manual App Registration Configuration](./ManualAppRegistrationConfiguration.md) for detailed manual setup instructions.
>  ![add_auth_provider_web_3](./images/add_auth_provider_web_3.png)



1. Add Authentication Provider in API Service

   - Go to deployed Container App and select `ca-cps-<randomname>-api` and click **Add Identity Provider** button in Authentication.  
     ![add_auth_provider_api_1](./images/add_auth_provider_api_1.png)

   - Select **Microsoft** and set **Client secret expiration**.  
     ![add_auth_provider_api_2](./images/add_auth_provider_api_2.png)

   - Set **Unauthenticated requests**, then click **Add** button.  
     ![add_auth_provider_api_3](./images/add_auth_provider_api_3.png)

## Step 2: Configure Application Registration - Web Application

1. Set Redirect URI in Single Page Application Platform

   - Go to deployed Container App `ca-cps-<randomname>-web` and select **Authentication** menu, then select created Application Registration.  
     ![configure_app_registration_web_1](./images/configure_app_registration_web_1.png)

   - Select **Authentication**, then select **+ Add a platform** menu.  
     ![configure_app_registration_web_2](./images/configure_app_registration_web_2.png)

   - Select **Single-page application**.  
     ![configure_app_registration_web_3](./images/configure_app_registration_web_3.png)

   - Add Container App `ca-cps-<randomname>-web`'s URL.  
     ![configure_app_registration_web_4](./images/configure_app_registration_web_4.png)

   - You may get this URL from here in your Container App.  
     ![configure_app_registration_web_5](./images/configure_app_registration_web_5.png)

2. Add Permission and Grant Permission

   - Add Permission for API application. Select **+ Add a permission** button, then search API application with name `ca-cps-<randomname>-api`.  
     ![configure_app_registration_web_6](./images/configure_app_registration_web_6.png)  
     ![configure_app_registration_web_7](./images/configure_app_registration_web_7.png)

   - Grant admin consent to permissions.  
     ![configure_app_registration_web_8](./images/configure_app_registration_web_8.png)

     > ⚠️ **Granting Admin Consent:** If you don't have permission or aren't able to grant admin consent for the API permissions, please follow one of the steps below:<br/><br/>_Option 1 - Reach out to your Tenant Administrator:_ Contact your administrator to let them know your Application Registration ID and what permissions you woud like to have them consent and approve.<br/><br/>_Option 2 - Internal Microsoft Employees Only:_ Please refer to these detailed instructions on the admin consent granting process: [https://aka.ms/AzAdminConsentWiki](https://aka.ms/AzAdminConsentWiki)
     


3. Grab Scope Name for Impersonation

   - Select **Expose an API** in the left menu. Copy the Scope name, then paste it in some temporary place.  
     The copied text will be used for Web Application Environment variable - **APP_WEB_SCOPE**.  
     ![configure_app_registration_web_9](./images/configure_app_registration_web_9.png)

4. Grab Client Id for Web App

   - Select **Overview** in the left menu. Copy the Client Id, then paste it in some temporary place.  
     The copied text will be used for Web Application Environment variable - **APP_WEB_CLIENT_ID**.  
     ![configure_app_registration_web_10](./images/configure_app_registration_web_10.png)

## Step 3: Configure Application Registration - API Application

1. Add the `user_impersonation` Scope to the API (Important!)

   - Go to deployed Container App `ca-cps-<randomname>-api` and select **Authentication** menu, then select created Application Registration.  
     ![configure_app_registration_api_1](./images/configure_app_registration_api_1.png)

   - Select **Expose an API** in the left menu.
   
   - If you don't see any scopes defined, click on **+ Add a scope** to add the required scope.
     - For Application ID URI, use the default (automatically generated) or enter a custom URI if needed
     - Add the following scope details:
       - Scope name: `user_impersonation`
       - Admin consent display name: `Access API App`
       - Admin consent description: `Allows the app to access the API application as the signed-in user`
     - Click **Add scope**

   > ⚠️ **Important:** This step is crucial for authentication to work properly. If this scope is not added, clients will receive a "AADSTS650057: Invalid resource" error when trying to authenticate.

2. Grab Scope Name for Impersonation

   - Once the scope is created, copy the full scope name (it should look like `api://{client-id}/user_impersonation`), then paste it in some temporary place.  
     The copied text will be used for Web Application Environment variable - **APP_API_SCOPE**.  
     ![configure_app_registration_api_2](./images/configure_app_registration_api_2.png)

## Step 4: Add Web Application's Client Id to Allowed Client Applications List in API Application Registration

1. Go to the deployed Container App `ca-cps-<randomname>-api`, select **Authentication**, and then click **Edit**.  
   ![add_client_id_to_api_1](./images/add_client_id_to_api_1.png)

2. Select **Allow requests from specific client applications**, then click the **pencil** icon to add the Client Id.  
   ![add_client_id_to_api_2](./images/add_client_id_to_api_2.png)

3. Add the **Client Id** obtained from [Step 2: Configure Application Registration - Web Application](#step-2-configure-application-registration---web-application), then save.  
   ![add_client_id_to_web_3](./images/add_client_id_to_web_3.png)

## Step 5: Update Environment Variable in Container App for Web Application

In previous steps for [Configure Application Registration - Web Application](#step-2-configure-application-registration---web-application) and [Configure Application Registration - API Application](#step-3-configure-application-registration---api-application), we grabbed Client Id for Web App's Application Registration and Scopes for Web and API's Application Registration.

Now, we will edit and deploy the Web Application Container with updated Environment variables.

1. Select **Containers** menu under **Application**. Then click **Environment variables** tab.
![update_env_app_1_1](./images/update_env_app_1_1.png)
2. Update 3 values which were taken in previous steps for **APP_WEB_CLIENT_ID**, **APP_WEB_SCOPE**, **APP_API_SCOPE**.  
Click on **Save as a new revision**.
   The updated revision will be activated soon.

## Conclusion

You have successfully configured the front-end and back-end Azure App Registrations with proper API permissions and security settings.

## Authenticating Using Azure CLI

If you need to authenticate to the API using Azure CLI (for scripting or testing purposes), you can use one of the following commands:

### Option 1: Login with scope

```bash
az login --scope api://<api_client_id>/user_impersonation
```

Replace `<api_client_id>` with your API application's client ID.

### Option 2: Get an access token

```bash
az account get-access-token --scope api://<api_client_id>/user_impersonation
```

Replace `<api_client_id>` with your API application's client ID.

## Troubleshooting

### Common Errors

#### AADSTS650057: Invalid resource

Error message: `AADSTS650057: Invalid resource. List of valid resources from app registration: . (the list is empty)`

**Cause**: This error occurs when the API application doesn't have any scopes exposed in its App Registration.

**Solution**: 
1. Go to the API Application Registration in Azure Portal
2. Navigate to "Expose an API"
3. Verify that the `user_impersonation` scope is created (or add it if missing) as described in [Step 3.1](#step-3-configure-application-registration---api-application)
4. Make sure to use the correct scope format when authenticating: `api://<api_client_id>/user_impersonation`

#### HTTP 401 Unauthorized

**Cause**: This error may occur when:
- The token doesn't have the required scopes
- The API application doesn't recognize the token's audience
- The token is invalid or expired

**Solution**:
1. Verify that you have added the API permissions and granted admin consent as described in [Step 2.2](#step-2-configure-application-registration---web-application)
2. Verify that the web application's client ID is added to the allowed client applications list as described in [Step 4](#step-4-add-web-applications-client-id-to-allowed-client-applications-list-in-api-application-registration)
3. Check that your token includes the correct scopes
4. Ensure that both App Registrations are properly configured