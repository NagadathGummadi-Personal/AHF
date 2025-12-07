enum ToolType {
  function,
  http,
  db,
}

enum ToolStatus {
  draft,
  pendingReview,
  approved,
  rejected,
  published,
}

enum ToolReturnType {
  json,
  text,
}

enum ToolReturnTarget {
  human,
  llm,
  agent,
  step,
}

class ToolParameter {
  final String name;
  final String description;
  final String type;
  final bool required;
  final dynamic defaultValue;
  final List<String>? enumValues;
  final String? dynamicVariable;

  ToolParameter({
    required this.name,
    required this.description,
    this.type = 'string',
    this.required = false,
    this.defaultValue,
    this.enumValues,
    this.dynamicVariable,
  });

  factory ToolParameter.fromJson(Map<String, dynamic> json) {
    return ToolParameter(
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      type: json['type'] ?? json['param_type'] ?? 'string',
      required: json['required'] ?? false,
      defaultValue: json['default'],
      enumValues: (json['enum'] as List?)?.cast<String>(),
      dynamicVariable: json['dynamic_variable'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'description': description,
      'type': type,
      'required': required,
      if (defaultValue != null) 'default': defaultValue,
      if (enumValues != null) 'enum': enumValues,
      if (dynamicVariable != null) 'dynamic_variable': dynamicVariable,
    };
  }
}

class RetryConfig {
  final bool enabled;
  final int maxRetries;
  final double backoffMultiplier;
  final int initialDelayMs;

  RetryConfig({
    this.enabled = false,
    this.maxRetries = 3,
    this.backoffMultiplier = 2.0,
    this.initialDelayMs = 1000,
  });

  factory RetryConfig.fromJson(Map<String, dynamic>? json) {
    if (json == null) return RetryConfig();
    return RetryConfig(
      enabled: json['enabled'] ?? false,
      maxRetries: json['max_retries'] ?? 3,
      backoffMultiplier: (json['backoff_multiplier'] ?? 2.0).toDouble(),
      initialDelayMs: json['initial_delay_ms'] ?? 1000,
    );
  }

  Map<String, dynamic> toJson() => {
    'enabled': enabled,
    'max_retries': maxRetries,
    'backoff_multiplier': backoffMultiplier,
    'initial_delay_ms': initialDelayMs,
  };
}

class IdempotencyConfig {
  final bool enabled;
  final int ttlSeconds;
  final List<String> keyFields;
  final bool bypassOnMissingKey;

  IdempotencyConfig({
    this.enabled = false,
    this.ttlSeconds = 3600,
    this.keyFields = const [],
    this.bypassOnMissingKey = false,
  });

  factory IdempotencyConfig.fromJson(Map<String, dynamic>? json) {
    if (json == null) return IdempotencyConfig();
    return IdempotencyConfig(
      enabled: json['enabled'] ?? false,
      ttlSeconds: json['ttl_s'] ?? 3600,
      keyFields: (json['key_fields'] as List?)?.cast<String>() ?? [],
      bypassOnMissingKey: json['bypass_on_missing_key'] ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'enabled': enabled,
    'ttl_s': ttlSeconds,
    'key_fields': keyFields,
    'bypass_on_missing_key': bypassOnMissingKey,
  };
}

class Tool {
  final String id;
  final String name;
  final String description;
  final ToolType type;
  final ToolStatus status;
  final String version;
  final List<ToolParameter> parameters;
  final String? createdBy;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  
  // Return configuration
  final ToolReturnType returnType;
  final ToolReturnTarget returnTarget;
  
  // Execution configuration
  final int timeoutSeconds;
  final RetryConfig retry;
  final IdempotencyConfig idempotency;

  // Advanced configs
  final Map<String, dynamic>? dynamicVariables;
  final Map<String, dynamic>? security;
  final Map<String, dynamic>? validation;

  
  // HTTP tool specific
  final String? url;
  final String? method;
  final Map<String, String>? headers;
  final Map<String, String>? queryParams;
  
  // Function tool specific
  final String? functionCode;
  
  // DB tool specific
  final String? driver;
  final String? host;
  final int? port;
  final String? database;

  Tool({
    required this.id,
    required this.name,
    required this.description,
    required this.type,
    this.status = ToolStatus.draft,
    this.version = '1.0.0',
    this.parameters = const [],
    this.createdBy,
    this.createdAt,
    this.updatedAt,
    this.returnType = ToolReturnType.json,
    this.returnTarget = ToolReturnTarget.llm,
    this.timeoutSeconds = 30,
    RetryConfig? retry,
    IdempotencyConfig? idempotency,
    this.url,
    this.method,
    this.headers,
    this.queryParams,
    this.functionCode,
    this.driver,
    this.host,
    this.port,
    this.database,
    this.dynamicVariables,
    this.security,
    this.validation,
  }) : retry = retry ?? RetryConfig(),
       idempotency = idempotency ?? IdempotencyConfig();

  factory Tool.fromJson(Map<String, dynamic> json) {
    return Tool(
      id: json['id'] ?? json['tool_id'] ?? '',
      name: json['tool_name'] ?? json['name'] ?? '',
      description: json['description'] ?? '',
      type: _parseToolType(json['tool_type']),
      status: _parseToolStatus(json['_metadata']?['status']),
      version: json['version'] ?? '1.0.0',
      parameters: (json['parameters'] as List<dynamic>?)
          ?.map((p) => ToolParameter.fromJson(p))
          .toList() ?? [],
      createdBy: json['owner'] ?? json['created_by'] ?? json['_metadata']?['created_by'],
      createdAt: json['_metadata']?['created_at'] != null 
          ? DateTime.tryParse(json['_metadata']['created_at']) 
          : null,
      updatedAt: json['_metadata']?['updated_at'] != null 
          ? DateTime.tryParse(json['_metadata']['updated_at']) 
          : null,
      returnType: _parseReturnType(json['return_type']),
      returnTarget: _parseReturnTarget(json['return_target']),
      timeoutSeconds: json['timeout_s'] ?? 30,
      retry: RetryConfig.fromJson(json['retry']),
      idempotency: IdempotencyConfig.fromJson(json['idempotency']),
      dynamicVariables: json['dynamic_variables'] != null
          ? Map<String, dynamic>.from(json['dynamic_variables'])
          : null,
      security: json['security'] != null
          ? Map<String, dynamic>.from(json['security'])
          : null,
      validation: json['validation'] != null
          ? Map<String, dynamic>.from(json['validation'])
          : null,
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
    );
  }

  Map<String, dynamic> toJson() {
    final data = <String, dynamic>{
      'id': id,
      'tool_name': name,
      'description': description,
      'tool_type': type.name,
      'parameters': parameters.map((p) => p.toJson()).toList(),
      'timeout_s': timeoutSeconds,
      'return_type': returnType.name,
      'return_target': returnTarget.name,
    };
    
    if (createdBy != null) data['owner'] = createdBy;
    
    // HTTP specific
    if (type == ToolType.http) {
      if (url != null) data['url'] = url;
      if (method != null) data['method'] = method;
      if (headers != null) data['headers'] = headers;
      if (queryParams != null) data['query_params'] = queryParams;
    }
    
    // Function specific
    if (type == ToolType.function) {
      if (functionCode != null) data['function_code'] = functionCode;
    }
    
    // DB specific
    if (type == ToolType.db) {
      if (driver != null) data['driver'] = driver;
      if (host != null) data['host'] = host;
      if (port != null) data['port'] = port;
      if (database != null) data['database'] = database;
    }
    
    // Retry config (only if enabled)
    if (retry.enabled) {
      data['retry'] = retry.toJson();
    }
    
    // Idempotency config (only if enabled)
    if (idempotency.enabled) {
      data['idempotency'] = idempotency.toJson();
    }

    if (dynamicVariables != null) data['dynamic_variables'] = dynamicVariables;
    if (security != null) data['security'] = security;
    if (validation != null) data['validation'] = validation;
    
    return data;
  }

  static ToolType _parseToolType(String? type) {
    switch (type?.toLowerCase()) {
      case 'http':
        return ToolType.http;
      case 'db':
      case 'database':
        return ToolType.db;
      case 'function':
      default:
        return ToolType.function;
    }
  }

  static ToolStatus _parseToolStatus(String? status) {
    switch (status?.toLowerCase()) {
      case 'pending_review':
        return ToolStatus.pendingReview;
      case 'approved':
        return ToolStatus.approved;
      case 'rejected':
        return ToolStatus.rejected;
      case 'published':
        return ToolStatus.published;
      case 'draft':
      default:
        return ToolStatus.draft;
    }
  }

  static ToolReturnType _parseReturnType(String? type) {
    switch (type?.toLowerCase()) {
      case 'text':
        return ToolReturnType.text;
      case 'json':
      default:
        return ToolReturnType.json;
    }
  }

  static ToolReturnTarget _parseReturnTarget(String? target) {
    switch (target?.toLowerCase()) {
      case 'human':
        return ToolReturnTarget.human;
      case 'agent':
        return ToolReturnTarget.agent;
      case 'step':
        return ToolReturnTarget.step;
      case 'llm':
      default:
        return ToolReturnTarget.llm;
    }
  }

  String get typeLabel {
    switch (type) {
      case ToolType.function:
        return 'Function';
      case ToolType.http:
        return 'HTTP';
      case ToolType.db:
        return 'Database';
    }
  }

  String get statusLabel {
    switch (status) {
      case ToolStatus.draft:
        return 'Draft';
      case ToolStatus.pendingReview:
        return 'Pending Review';
      case ToolStatus.approved:
        return 'Approved';
      case ToolStatus.rejected:
        return 'Rejected';
      case ToolStatus.published:
        return 'Published';
    }
  }

  Tool copyWith({
    String? id,
    String? name,
    String? description,
    ToolType? type,
    ToolStatus? status,
    String? version,
    List<ToolParameter>? parameters,
    String? createdBy,
    DateTime? createdAt,
    DateTime? updatedAt,
    ToolReturnType? returnType,
    ToolReturnTarget? returnTarget,
    int? timeoutSeconds,
    RetryConfig? retry,
    IdempotencyConfig? idempotency,
    Map<String, dynamic>? dynamicVariables,
    Map<String, dynamic>? security,
    Map<String, dynamic>? validation,
    String? url,
    String? method,
    Map<String, String>? headers,
    Map<String, String>? queryParams,
    String? functionCode,
    String? driver,
    String? host,
    int? port,
    String? database,
  }) {
    return Tool(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      type: type ?? this.type,
      status: status ?? this.status,
      version: version ?? this.version,
      parameters: parameters ?? this.parameters,
      createdBy: createdBy ?? this.createdBy,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      returnType: returnType ?? this.returnType,
      returnTarget: returnTarget ?? this.returnTarget,
      timeoutSeconds: timeoutSeconds ?? this.timeoutSeconds,
      retry: retry ?? this.retry,
      idempotency: idempotency ?? this.idempotency,
      dynamicVariables: dynamicVariables ?? this.dynamicVariables,
      security: security ?? this.security,
      validation: validation ?? this.validation,
      url: url ?? this.url,
      method: method ?? this.method,
      headers: headers ?? this.headers,
      queryParams: queryParams ?? this.queryParams,
      functionCode: functionCode ?? this.functionCode,
      driver: driver ?? this.driver,
      host: host ?? this.host,
      port: port ?? this.port,
      database: database ?? this.database,
    );
  }
}
