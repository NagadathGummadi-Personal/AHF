import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/tool.dart';

class ToolsProvider extends ChangeNotifier {
  List<Tool> _tools = [];
  Tool? _selectedTool;
  bool _isLoading = false;
  String? _error;
  String _searchQuery = '';
  ToolType? _filterType;
  String? _authToken;

  // API Base URL - configure based on environment
  static const String _baseUrl = 'http://localhost:8000/api/v1';

  List<Tool> get tools {
    var filtered = _tools;
    
    if (_searchQuery.isNotEmpty) {
      final query = _searchQuery.toLowerCase();
      filtered = filtered.where((t) => 
        t.name.toLowerCase().contains(query) ||
        t.description.toLowerCase().contains(query)
      ).toList();
    }
    
    if (_filterType != null) {
      filtered = filtered.where((t) => t.type == _filterType).toList();
    }
    
    return filtered;
  }

  Tool? get selectedTool => _selectedTool;
  bool get isLoading => _isLoading;
  String? get error => _error;
  String get searchQuery => _searchQuery;
  ToolType? get filterType => _filterType;

  ToolsProvider() {
    // Lazy loading: Don't fetch immediately
  }

  void updateAuthToken(String? token) {
    _authToken = token;
  }

  Map<String, String> _headers({bool jsonContent = false}) {
    return {
      if (jsonContent) 'Content-Type': 'application/json',
      if (_authToken != null && _authToken!.isNotEmpty) 'Authorization': 'Bearer $_authToken',
    };
  }

  void setSearchQuery(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  void setFilterType(ToolType? type) {
    _filterType = type;
    notifyListeners();
  }

  void selectTool(Tool? tool) {
    _selectedTool = tool;
    notifyListeners();
    if (tool != null) {
      _loadFullSpec(tool.id);
    }
  }

  Future<void> _loadFullSpec(String id) async {
    try {
      final detailed = await getTool(id);
      if (detailed != null) {
        _selectedTool = detailed;
        // also update list entry with full spec if helpful
        final idx = _tools.indexWhere((t) => t.id == id);
        if (idx >= 0) {
          _tools[idx] = detailed;
        }
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error loading full tool spec: $e');
    }
  }

  Future<void> fetchTools() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/tools'),
        headers: _headers(),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _tools = (data['tools'] as List?)
            ?.map((t) => Tool.fromJson(t))
            .toList() ?? [];
        _error = null;
      } else {
        _error = 'Failed to load tools: ${response.statusCode}';
        _tools = [];
      }
    } catch (e) {
      _error = 'Cannot connect to server. Make sure the API is running at $_baseUrl';
      _tools = [];
      debugPrint('Error fetching tools: $e');
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<Tool?> getTool(String id, {String? version}) async {
    try {
      var url = '$_baseUrl/tools/$id';
      if (version != null) {
        url += '?version=$version';
      }
      final response = await http.get(
        Uri.parse(url),
        headers: _headers(),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return Tool.fromJson(data['data']);
      }
    } catch (e) {
      debugPrint('Error fetching tool: $e');
    }
    return null;
  }

  Future<Map<String, dynamic>> createTool(Tool tool) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/tools'),
        headers: _headers(jsonContent: true),
        body: json.encode(tool.toJson()),
      );
      
      final data = json.decode(response.body);
      
      if (response.statusCode == 201) {
        await fetchTools();
        return {'success': true, 'message': data['message'] ?? 'Tool created successfully'};
      } else {
        return {'success': false, 'message': data['detail'] ?? 'Failed to create tool'};
      }
    } catch (e) {
      debugPrint('Error creating tool: $e');
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  Future<Map<String, dynamic>> updateTool(Tool tool) async {
    try {
      final response = await http.put(
        Uri.parse('$_baseUrl/tools/${tool.id}'),
        headers: _headers(jsonContent: true),
        body: json.encode(tool.toJson()),
      );
      
      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        await fetchTools();
        return {'success': true, 'message': data['message'] ?? 'Tool updated successfully'};
      } else {
        return {'success': false, 'message': data['detail'] ?? 'Failed to update tool'};
      }
    } catch (e) {
      debugPrint('Error updating tool: $e');
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  Future<Map<String, dynamic>> deleteTool(String id) async {
    try {
      final response = await http.delete(
        Uri.parse('$_baseUrl/tools/$id'),
        headers: _headers(),
      );
      
      if (response.statusCode == 200) {
        if (_selectedTool?.id == id) {
          _selectedTool = null;
        }
        await fetchTools();
        return {'success': true, 'message': 'Tool deleted successfully'};
      } else {
        final data = json.decode(response.body);
        return {'success': false, 'message': data['detail'] ?? 'Failed to delete tool'};
      }
    } catch (e) {
      debugPrint('Error deleting tool: $e');
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  Future<Map<String, dynamic>> submitForReview(String id, {String? notes}) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/tools/$id/submit-review'),
        headers: _headers(jsonContent: true),
        body: json.encode({'notes': notes}),
      );
      
      final data = json.decode(response.body);
      
      if (response.statusCode == 200) {
        await fetchTools();
        return {'success': true, 'message': 'Tool submitted for review'};
      } else {
        return {'success': false, 'message': data['detail'] ?? 'Failed to submit'};
      }
    } catch (e) {
      debugPrint('Error submitting for review: $e');
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  // Execute/test a tool with given parameters
  Future<Map<String, dynamic>> executeTool(Tool tool, Map<String, dynamic> params) async {
    // For now, simulate execution locally
    // In production, this would call an execution endpoint
    await Future.delayed(const Duration(milliseconds: 500));
    
    return {
      'success': true,
      'result': {
        'message': 'Tool execution simulated',
        'input': params,
        'tool_id': tool.id,
        'tool_name': tool.name,
      },
      'execution_time_ms': 500,
    };
  }

  // Generate Python code template for function tools
  String generateFunctionTemplate(String functionName, List<ToolParameter> parameters) {
    final docParams = parameters.map((p) => 
      '        ${p.name}: ${p.description}'
    ).join('\n');

    return '''from typing import Any, Dict, List

async def $functionName(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    ${functionName.replaceAll('_', ' ').split(' ').map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}').join(' ')}
    
    Args:
        args: Dictionary containing:
$docParams
    
    Returns:
        Dict containing the result
    """
    # Extract parameters
${parameters.map((p) => "    ${p.name} = args.get('${p.name}')").join('\n')}
    
    # TODO: Implement your logic here
    result = {
        "status": "success",
        "data": {
${parameters.map((p) => '            "${p.name}": ${p.name},').join('\n')}
        }
    }
    
    return result
''';
  }
}
