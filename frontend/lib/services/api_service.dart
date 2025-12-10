import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

/// Generic API service for making HTTP requests.
class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;
  ApiService._internal();
  
  /// GET request
  Future<ApiResponse<T>> get<T>(
    String endpoint, {
    Map<String, String>? headers,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
        headers: {...ApiConfig.defaultHeaders, ...?headers},
      ).timeout(ApiConfig.timeout);
      
      return _handleResponse(response, fromJson);
    } catch (e) {
      return ApiResponse.error(e.toString());
    }
  }
  
  /// POST request
  Future<ApiResponse<T>> post<T>(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
        headers: {...ApiConfig.defaultHeaders, ...?headers},
        body: body != null ? jsonEncode(body) : null,
      ).timeout(ApiConfig.timeout);
      
      return _handleResponse(response, fromJson);
    } catch (e) {
      return ApiResponse.error(e.toString());
    }
  }
  
  /// PUT request
  Future<ApiResponse<T>> put<T>(
    String endpoint, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await http.put(
        Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
        headers: {...ApiConfig.defaultHeaders, ...?headers},
        body: body != null ? jsonEncode(body) : null,
      ).timeout(ApiConfig.timeout);
      
      return _handleResponse(response, fromJson);
    } catch (e) {
      return ApiResponse.error(e.toString());
    }
  }
  
  /// DELETE request
  Future<ApiResponse<T>> delete<T>(
    String endpoint, {
    Map<String, String>? headers,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await http.delete(
        Uri.parse('${ApiConfig.apiBaseUrl}$endpoint'),
        headers: {...ApiConfig.defaultHeaders, ...?headers},
      ).timeout(ApiConfig.timeout);
      
      return _handleResponse(response, fromJson);
    } catch (e) {
      return ApiResponse.error(e.toString());
    }
  }
  
  ApiResponse<T> _handleResponse<T>(
    http.Response response,
    T Function(dynamic)? fromJson,
  ) {
    final body = response.body.isNotEmpty ? jsonDecode(response.body) : null;
    
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = fromJson != null && body != null ? fromJson(body) : body as T?;
      return ApiResponse.success(data);
    } else {
      final message = body is Map ? body['detail'] ?? body['message'] ?? 'Request failed' : 'Request failed';
      return ApiResponse.error(message.toString(), statusCode: response.statusCode);
    }
  }
}

/// API response wrapper
class ApiResponse<T> {
  final T? data;
  final String? error;
  final int? statusCode;
  final bool isSuccess;
  
  ApiResponse._({
    this.data,
    this.error,
    this.statusCode,
    required this.isSuccess,
  });
  
  factory ApiResponse.success(T? data) => ApiResponse._(
    data: data,
    isSuccess: true,
    statusCode: 200,
  );
  
  factory ApiResponse.error(String error, {int? statusCode}) => ApiResponse._(
    error: error,
    statusCode: statusCode,
    isSuccess: false,
  );
}


