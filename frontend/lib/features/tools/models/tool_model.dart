/// Simplified Tool model for UI display and editing.
/// 
/// This is a frontend model that maps to the backend ToolSpec.
/// For complex nested configurations, we use Map<String, dynamic>.
class Tool {
  final String id;
  final String toolName;
  final String description;
  final String toolType;
  final String version;
  final List<ToolParameter> parameters;
  final int timeoutS;
  final String returnType;
  final String returnTarget;
  final String? owner;
  
  // HTTP specific
  final String? url;
  final String? method;
  final Map<String, String>? headers;
  final Map<String, String>? queryParams;
  
  // Function specific
  final String? functionCode;
  
  // DB specific
  final String? driver;
  final String? host;
  final int? port;
  final String? database;
  
  // Advanced configs (stored as maps for flexibility)
  final Map<String, dynamic>? retry;
  final Map<String, dynamic>? circuitBreaker;
  final Map<String, dynamic>? idempotency;
  final Map<String, dynamic>? preToolSpeech;
  final Map<String, dynamic>? dynamicVariables;
  
  // Metadata
  final DateTime? createdAt;
  final DateTime? updatedAt;
  
  const Tool({
    required this.id,
    required this.toolName,
    required this.description,
    required this.toolType,
    this.version = '1.0.0',
    this.parameters = const [],
    this.timeoutS = 30,
    this.returnType = 'json',
    this.returnTarget = 'llm',
    this.owner,
    this.url,
    this.method,
    this.headers,
    this.queryParams,
    this.functionCode,
    this.driver,
    this.host,
    this.port,
    this.database,
    this.retry,
    this.circuitBreaker,
    this.idempotency,
    this.preToolSpeech,
    this.dynamicVariables,
    this.createdAt,
    this.updatedAt,
  });
  
  factory Tool.fromJson(Map<String, dynamic> json) {
    return Tool(
      id: json['id'] ?? '',
      toolName: json['tool_name'] ?? json['name'] ?? '',
      description: json['description'] ?? '',
      toolType: json['tool_type'] ?? 'function',
      version: json['version'] ?? '1.0.0',
      parameters: (json['parameters'] as List?)
          ?.map((p) => ToolParameter.fromJson(p))
          .toList() ?? [],
      timeoutS: json['timeout_s'] ?? 30,
      returnType: json['return_type'] ?? json['returns'] ?? 'json',
      returnTarget: json['return_target'] ?? 'llm',
      owner: json['owner'],
      url: json['url'],
      method: json['method'],
      headers: json['headers'] != null
          ? Map<String, String>.from(json['headers'])
          : null,
      queryParams: json['query_params'] != null
          ? Map<String, String>.from(json['query_params'])
          : null,
      functionCode: json['function_code'],
      driver: json['driver'],
      host: json['host'],
      port: json['port'],
      database: json['database'],
      retry: json['retry'],
      circuitBreaker: json['circuit_breaker'],
      idempotency: json['idempotency'],
      preToolSpeech: json['pre_tool_speech'],
      dynamicVariables: json['dynamic_variables'],
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'])
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'])
          : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'id': id,
      'tool_name': toolName,
      'description': description,
      'tool_type': toolType,
      'version': version,
      'parameters': parameters.map((p) => p.toJson()).toList(),
      'timeout_s': timeoutS,
      'return_type': returnType,
      'return_target': returnTarget,
    };
    
    if (owner != null) json['owner'] = owner;
    
    // HTTP fields
    if (toolType == 'http') {
      if (url != null) json['url'] = url;
      if (method != null) json['method'] = method;
      if (headers != null && headers!.isNotEmpty) json['headers'] = headers;
      if (queryParams != null && queryParams!.isNotEmpty) json['query_params'] = queryParams;
    }
    
    // Function fields
    if (toolType == 'function') {
      if (functionCode != null) json['function_code'] = functionCode;
    }
    
    // DB fields
    if (toolType == 'db') {
      if (driver != null) json['driver'] = driver;
      if (host != null) json['host'] = host;
      if (port != null) json['port'] = port;
      if (database != null) json['database'] = database;
    }
    
    // Advanced configs
    if (retry != null) json['retry'] = retry;
    if (circuitBreaker != null) json['circuit_breaker'] = circuitBreaker;
    if (idempotency != null) json['idempotency'] = idempotency;
    if (preToolSpeech != null) json['pre_tool_speech'] = preToolSpeech;
    if (dynamicVariables != null) json['dynamic_variables'] = dynamicVariables;
    
    return json;
  }
  
  Tool copyWith({
    String? id,
    String? toolName,
    String? description,
    String? toolType,
    String? version,
    List<ToolParameter>? parameters,
    int? timeoutS,
    String? returnType,
    String? returnTarget,
    String? owner,
    String? url,
    String? method,
    Map<String, String>? headers,
    Map<String, String>? queryParams,
    String? functionCode,
    String? driver,
    String? host,
    int? port,
    String? database,
    Map<String, dynamic>? retry,
    Map<String, dynamic>? circuitBreaker,
    Map<String, dynamic>? idempotency,
    Map<String, dynamic>? preToolSpeech,
    Map<String, dynamic>? dynamicVariables,
  }) {
    return Tool(
      id: id ?? this.id,
      toolName: toolName ?? this.toolName,
      description: description ?? this.description,
      toolType: toolType ?? this.toolType,
      version: version ?? this.version,
      parameters: parameters ?? this.parameters,
      timeoutS: timeoutS ?? this.timeoutS,
      returnType: returnType ?? this.returnType,
      returnTarget: returnTarget ?? this.returnTarget,
      owner: owner ?? this.owner,
      url: url ?? this.url,
      method: method ?? this.method,
      headers: headers ?? this.headers,
      queryParams: queryParams ?? this.queryParams,
      functionCode: functionCode ?? this.functionCode,
      driver: driver ?? this.driver,
      host: host ?? this.host,
      port: port ?? this.port,
      database: database ?? this.database,
      retry: retry ?? this.retry,
      circuitBreaker: circuitBreaker ?? this.circuitBreaker,
      idempotency: idempotency ?? this.idempotency,
      preToolSpeech: preToolSpeech ?? this.preToolSpeech,
      dynamicVariables: dynamicVariables ?? this.dynamicVariables,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }
  
  /// Get display-friendly tool type label
  String get toolTypeLabel {
    switch (toolType) {
      case 'function':
        return 'Function';
      case 'http':
        return 'HTTP';
      case 'db':
        return 'Database';
      default:
        return toolType;
    }
  }
  
  /// Create an empty tool with defaults
  factory Tool.empty({String type = 'function'}) {
    return Tool(
      id: '',
      toolName: '',
      description: '',
      toolType: type,
    );
  }
}

/// Tool parameter model.
class ToolParameter {
  final String name;
  final String description;
  final String type;
  final bool required;
  final dynamic defaultValue;
  final List<String>? enumValues;
  
  const ToolParameter({
    required this.name,
    this.description = '',
    this.type = 'string',
    this.required = false,
    this.defaultValue,
    this.enumValues,
  });
  
  factory ToolParameter.fromJson(Map<String, dynamic> json) {
    return ToolParameter(
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      type: json['type'] ?? json['param_type'] ?? 'string',
      required: json['required'] ?? false,
      defaultValue: json['default'],
      enumValues: (json['enum'] as List?)?.cast<String>(),
    );
  }
  
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'name': name,
      'description': description,
      'type': type,
      'required': required,
    };
    
    if (defaultValue != null) json['default'] = defaultValue;
    if (enumValues != null) json['enum'] = enumValues;
    
    return json;
  }
  
  ToolParameter copyWith({
    String? name,
    String? description,
    String? type,
    bool? required,
    dynamic defaultValue,
    List<String>? enumValues,
  }) {
    return ToolParameter(
      name: name ?? this.name,
      description: description ?? this.description,
      type: type ?? this.type,
      required: required ?? this.required,
      defaultValue: defaultValue ?? this.defaultValue,
      enumValues: enumValues ?? this.enumValues,
    );
  }
}


