import 'package:flutter/foundation.dart';

import '../config/auth_config.dart';
import '../services/msal_web.dart';

class AuthProvider extends ChangeNotifier {
  final MsalWeb _msal = MsalWeb();

  bool _isInitialized = false;
  bool _isBusy = false;
  bool _isAuthenticated = false;
  String? _accessToken;
  String? _idToken;
  String? _displayName;
  String? _email;
  String? _error;

  bool get isInitialized => _isInitialized;
  bool get isBusy => _isBusy;
  bool get isAuthenticated => _isAuthenticated;
  String? get accessToken => _accessToken;
  String? get idToken => _idToken;
  String? get displayName => _displayName ?? _email;
  String? get email => _email;
  String? get error => _error;

  Future<void> initialize() async {
    if (_isInitialized && _error == null) return;
    _isBusy = true;
    _error = null;
    notifyListeners();

    try {
      if (!kIsWeb) {
        _error = 'Microsoft sign-in is only available on web in this build.';
        return;
      }

      if (AuthConfig.clientId.isEmpty || AuthConfig.clientId == 'YOUR_CLIENT_ID') {
        _error = 'Configure MSAL_CLIENT_ID and MSAL_TENANT_ID to enable Microsoft sign-in.';
        return;
      }

      final redirect = AuthConfig.resolveRedirectUri(Uri.base.origin);
      await _msal.init(
        clientId: AuthConfig.clientId,
        authority: AuthConfig.resolveAuthority(),
        redirectUri: redirect,
        scopes: AuthConfig.defaultScopes,
      );

      final account = await _msal.currentAccount();
      if (account != null) {
        final result = await _msal.acquireToken(AuthConfig.defaultScopes);
        _setSession(result);
      }
    } catch (e) {
      _error = e.toString();
    } finally {
      _isInitialized = true;
      _isBusy = false;
      notifyListeners();
    }
  }

  Future<bool> signIn() async {
    _isBusy = true;
    _error = null;
    notifyListeners();

    try {
      final result = await _msal.login(AuthConfig.defaultScopes);
      _setSession(result);
      return true;
    } catch (e) {
      _error = 'Microsoft sign-in failed: $e';
      _clearSession();
      return false;
    } finally {
      _isBusy = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    _isBusy = true;
    notifyListeners();

    try {
      if (kIsWeb) {
        await _msal.signOut();
      }
    } catch (_) {
      // Ignore sign-out errors to avoid blocking UX.
    } finally {
      _clearSession();
      _isBusy = false;
      notifyListeners();
    }
  }

  void _setSession(MsalAuthResult result) {
    _accessToken = result.accessToken;
    _idToken = result.idToken;
    _displayName = result.account?.name;
    _email = result.account?.username;
    _isAuthenticated = _accessToken?.isNotEmpty == true;
    _error = null;
  }

  void _clearSession() {
    _accessToken = null;
    _idToken = null;
    _displayName = null;
    _email = null;
    _isAuthenticated = false;
  }
}

