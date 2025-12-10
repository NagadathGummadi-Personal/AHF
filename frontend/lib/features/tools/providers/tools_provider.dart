import 'package:flutter/foundation.dart';
import '../../../services/api_service.dart';
import '../models/tool_model.dart';

/// Provider for managing tools state.
class ToolsProvider extends ChangeNotifier {
  final ApiService _api = ApiService();
  
  List<Tool> _tools = [];
  Tool? _selectedTool;
  bool _isLoading = false;
  String? _error;
  String _searchQuery = '';
  String? _filterType;
  
  // Getters
  List<Tool> get tools {
    var filtered = _tools;
    
    // Apply search filter
    if (_searchQuery.isNotEmpty) {
      final query = _searchQuery.toLowerCase();
      filtered = filtered.where((t) =>
        t.toolName.toLowerCase().contains(query) ||
        t.description.toLowerCase().contains(query) ||
        t.id.toLowerCase().contains(query)
      ).toList();
    }
    
    // Apply type filter
    if (_filterType != null) {
      filtered = filtered.where((t) => t.toolType == _filterType).toList();
    }
    
    return filtered;
  }
  
  Tool? get selectedTool => _selectedTool;
  bool get isLoading => _isLoading;
  String? get error => _error;
  String get searchQuery => _searchQuery;
  String? get filterType => _filterType;
  
  int get totalCount => _tools.length;
  int get functionCount => _tools.where((t) => t.toolType == 'function').length;
  int get httpCount => _tools.where((t) => t.toolType == 'http').length;
  int get dbCount => _tools.where((t) => t.toolType == 'db').length;
  
  /// Initialize and load tools
  Future<void> loadTools() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    final response = await _api.get<List<dynamic>>(
      '/tools',
      fromJson: (json) => json as List<dynamic>,
    );
    
    if (response.isSuccess && response.data != null) {
      _tools = response.data!.map((json) => Tool.fromJson(json)).toList();
      _error = null;
    } else {
      _error = response.error;
      // Load mock data for development
      _tools = _getMockTools();
    }
    
    _isLoading = false;
    notifyListeners();
  }
  
  /// Select a tool
  void selectTool(Tool? tool) {
    _selectedTool = tool;
    notifyListeners();
  }
  
  /// Set search query
  void setSearchQuery(String query) {
    _searchQuery = query;
    notifyListeners();
  }
  
  /// Set type filter
  void setFilterType(String? type) {
    _filterType = type;
    notifyListeners();
  }
  
  /// Create a new tool
  Future<Map<String, dynamic>> createTool(Tool tool) async {
    final response = await _api.post(
      '/tools',
      body: tool.toJson(),
    );
    
    if (response.isSuccess) {
      await loadTools();
      return {'success': true, 'message': 'Tool created successfully'};
    }
    return {'success': false, 'message': response.error ?? 'Failed to create tool'};
  }
  
  /// Update an existing tool
  Future<Map<String, dynamic>> updateTool(Tool tool) async {
    final response = await _api.put(
      '/tools/${tool.id}',
      body: tool.toJson(),
    );
    
    if (response.isSuccess) {
      await loadTools();
      if (_selectedTool?.id == tool.id) {
        _selectedTool = tool;
      }
      return {'success': true, 'message': 'Tool updated successfully'};
    }
    return {'success': false, 'message': response.error ?? 'Failed to update tool'};
  }
  
  /// Delete a tool
  Future<Map<String, dynamic>> deleteTool(String id) async {
    final response = await _api.delete('/tools/$id');
    
    if (response.isSuccess) {
      await loadTools();
      if (_selectedTool?.id == id) {
        _selectedTool = null;
      }
      return {'success': true, 'message': 'Tool deleted successfully'};
    }
    return {'success': false, 'message': response.error ?? 'Failed to delete tool'};
  }
  
  /// Mock data for development
  List<Tool> _getMockTools() {
    return [
      Tool(
        id: 'search-web-v1',
        toolName: 'Web Search',
        description: 'Search the web for information using a search engine API',
        toolType: 'http',
        version: '1.0.0',
        parameters: [
          ToolParameter(name: 'query', description: 'Search query string', required: true),
          ToolParameter(name: 'max_results', description: 'Maximum number of results', type: 'integer'),
        ],
        url: 'https://api.search.com/v1/search',
        method: 'GET',
        timeoutS: 30,
      ),
      Tool(
        id: 'calculate-v1',
        toolName: 'Calculator',
        description: 'Perform mathematical calculations',
        toolType: 'function',
        version: '1.0.0',
        parameters: [
          ToolParameter(name: 'expression', description: 'Mathematical expression to evaluate', required: true),
        ],
        functionCode: '''async def calculate(args: dict) -> dict:
    """Perform mathematical calculations."""
    expression = args.get('expression', '')
    try:
        result = eval(expression)
        return {'result': result}
    except Exception as e:
        return {'error': str(e)}''',
        timeoutS: 10,
      ),
      Tool(
        id: 'query-users-v1',
        toolName: 'Query Users',
        description: 'Query user data from the database',
        toolType: 'db',
        version: '1.0.0',
        parameters: [
          ToolParameter(name: 'user_id', description: 'User ID to query'),
          ToolParameter(name: 'email', description: 'Email address to search'),
        ],
        driver: 'postgresql',
        host: 'localhost',
        port: 5432,
        database: 'users_db',
        timeoutS: 30,
      ),
      Tool(
        id: 'send-email-v1',
        toolName: 'Send Email',
        description: 'Send an email to a recipient using the email service',
        toolType: 'http',
        version: '1.0.0',
        parameters: [
          ToolParameter(name: 'to', description: 'Recipient email address', required: true),
          ToolParameter(name: 'subject', description: 'Email subject', required: true),
          ToolParameter(name: 'body', description: 'Email body content', required: true),
        ],
        url: 'https://api.email.com/v1/send',
        method: 'POST',
        timeoutS: 60,
      ),
    ];
  }
}


