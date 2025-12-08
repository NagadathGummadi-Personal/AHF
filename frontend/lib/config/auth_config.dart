class AuthConfig {
  static const String clientId = String.fromEnvironment(
    'MSAL_CLIENT_ID',
    defaultValue: 'YOUR_CLIENT_ID',
  );

  static const String tenantId = String.fromEnvironment(
    'MSAL_TENANT_ID',
    defaultValue: 'common',
  );

  static const String redirectUri = String.fromEnvironment(
    'MSAL_REDIRECT_URI',
    defaultValue: '',
  );

  static const List<String> defaultScopes = [
    'User.Read',
    'openid',
    'profile',
    'email',
  ];

  static String resolveAuthority() {
    final tenant = tenantId.trim().isEmpty ? 'common' : tenantId.trim();
    return 'https://login.microsoftonline.com/$tenant';
  }

  static String resolveRedirectUri(String fallbackOrigin) {
    return redirectUri.isNotEmpty ? redirectUri : fallbackOrigin;
  }
}

