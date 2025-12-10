/// API configuration for the AHF backend.
class ApiConfig {
  ApiConfig._();
  
  /// Base URL for the API
  /// Change this based on environment
  static const String baseUrl = 'http://localhost:8000';
  
  /// API version prefix
  static const String apiVersion = '/api/v1';
  
  /// Full API base URL
  static String get apiBaseUrl => '$baseUrl$apiVersion';
  
  /// Endpoints
  static const String toolsEndpoint = '/tools';
  
  /// Full URLs
  static String get toolsUrl => '$apiBaseUrl$toolsEndpoint';
  
  /// Request timeout
  static const Duration timeout = Duration(seconds: 30);
  
  /// Default headers
  static Map<String, String> get defaultHeaders => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
}


