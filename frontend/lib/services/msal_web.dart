import 'dart:async';
// ignore: avoid_web_libraries_in_flutter, uri_does_not_exist
import 'dart:js_util' as js_util;

import 'package:flutter/foundation.dart';

class MsalAccount {
  final String? name;
  final String? username;
  final String? homeAccountId;
  final String? localAccountId;

  MsalAccount({
    this.name,
    this.username,
    this.homeAccountId,
    this.localAccountId,
  });
}

class MsalAuthResult {
  final String? accessToken;
  final String? idToken;
  final MsalAccount? account;

  const MsalAuthResult({
    this.accessToken,
    this.idToken,
    this.account,
  });
}

class MsalWeb {
  dynamic get _helper {
    final helper = js_util.getProperty(js_util.globalThis, 'msalHelper');
    if (helper == null) {
      throw StateError(
        'MSAL helper not found. Ensure web/index.html includes the helper script.',
      );
    }
    return helper;
  }

  void _ensureWeb() {
    if (!kIsWeb) {
      throw UnsupportedError('MSAL web helper can only be used on Web.');
    }
  }

  Future<void> init({
    required String clientId,
    required String authority,
    required String redirectUri,
    List<String> scopes = const ['User.Read'],
  }) async {
    _ensureWeb();
    final config = js_util.jsify({
      'clientId': clientId,
      'authority': authority,
      'redirectUri': redirectUri,
      'scopes': scopes,
    });

    await js_util.promiseToFuture(
      js_util.callMethod(_helper, 'init', [config]),
    );
  }

  Future<MsalAuthResult> login(List<String> scopes) async {
    _ensureWeb();
    final result = await js_util.promiseToFuture(
      js_util.callMethod(_helper, 'login', [js_util.jsify(scopes)]),
    );
    return _mapAuthResult(result);
  }

  Future<MsalAuthResult> acquireToken(List<String> scopes) async {
    _ensureWeb();
    final result = await js_util.promiseToFuture(
      js_util.callMethod(_helper, 'acquireToken', [js_util.jsify(scopes)]),
    );
    return _mapAuthResult(result);
  }

  Future<MsalAccount?> currentAccount() async {
    _ensureWeb();
    final account = js_util.callMethod(_helper, 'getAccount', []);
    if (account == null) return null;
    return _mapAccount(account);
  }

  Future<void> signOut() async {
    _ensureWeb();
    await js_util.promiseToFuture(
      js_util.callMethod(_helper, 'logout', []),
    );
  }

  MsalAuthResult _mapAuthResult(dynamic result) {
    if (result == null) {
      return const MsalAuthResult();
    }
    final accountObj = js_util.getProperty(result, 'account');
    return MsalAuthResult(
      accessToken: _getString(result, 'accessToken'),
      idToken: _getString(result, 'idToken'),
      account: accountObj != null ? _mapAccount(accountObj) : null,
    );
  }

  MsalAccount _mapAccount(dynamic accountObj) {
    return MsalAccount(
      name: _getString(accountObj, 'name'),
      username: _getString(accountObj, 'username'),
      homeAccountId: _getString(accountObj, 'homeAccountId'),
      localAccountId: _getString(accountObj, 'localAccountId'),
    );
  }

  String? _getString(dynamic obj, String key) {
    final value = js_util.getProperty(obj, key);
    if (value == null) return null;
    return value.toString();
  }
}

