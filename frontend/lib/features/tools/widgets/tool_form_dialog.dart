import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_theme.dart';
import '../models/tool_model.dart';
import '../providers/tools_provider.dart';

/// Multi-step dialog for creating/editing tools.
class ToolFormDialog extends StatefulWidget {
  final Tool? editTool;

  const ToolFormDialog({super.key, this.editTool});

  @override
  State<ToolFormDialog> createState() => _ToolFormDialogState();
}

class _ToolFormDialogState extends State<ToolFormDialog> {
  final _formKey = GlobalKey<FormState>();
  int _currentStep = 0;
  bool _isSubmitting = false;
  
  // Form data
  late String _toolType;
  late TextEditingController _idController;
  late TextEditingController _nameController;
  late TextEditingController _descriptionController;
  late TextEditingController _versionController;
  
  // HTTP fields
  late TextEditingController _urlController;
  late String _method;
  final List<MapEntry<String, String>> _headers = [];
  
  // Function fields
  late TextEditingController _codeController;
  
  // DB fields
  late String _driver;
  late TextEditingController _hostController;
  late TextEditingController _portController;
  late TextEditingController _databaseController;
  
  // Parameters
  final List<ToolParameter> _parameters = [];
  
  // Execution settings
  int _timeoutS = 30;
  String _returnType = 'json';
  String _returnTarget = 'llm';
  
  // Advanced configs
  final List<MapEntry<String, String>> _retryConfig = [];
  final List<MapEntry<String, String>> _idempotencyConfig = [];

  @override
  void initState() {
    super.initState();
    _initializeForm();
  }

  void _initializeForm() {
    final tool = widget.editTool;
    
    _toolType = tool?.toolType ?? 'function';
    _idController = TextEditingController(text: tool?.id ?? '');
    _nameController = TextEditingController(text: tool?.toolName ?? '');
    _descriptionController = TextEditingController(text: tool?.description ?? '');
    _versionController = TextEditingController(text: tool?.version ?? '1.0.0');
    
    // HTTP
    _urlController = TextEditingController(text: tool?.url ?? '');
    _method = tool?.method ?? 'GET';
    if (tool?.headers != null) {
      _headers.addAll(tool!.headers!.entries);
    }
    
    // Function
    _codeController = TextEditingController(text: tool?.functionCode ?? _getDefaultCode());
    
    // DB
    _driver = tool?.driver ?? 'postgresql';
    _hostController = TextEditingController(text: tool?.host ?? 'localhost');
    _portController = TextEditingController(text: tool?.port?.toString() ?? '5432');
    _databaseController = TextEditingController(text: tool?.database ?? '');
    
    // Parameters
    if (tool?.parameters != null) {
      _parameters.addAll(tool!.parameters);
    }
    
    // Execution
    _timeoutS = tool?.timeoutS ?? 30;
    _returnType = tool?.returnType ?? 'json';
    _returnTarget = tool?.returnTarget ?? 'llm';
    
    // Advanced configs
    if (tool?.retry != null) {
      _retryConfig.addAll(tool!.retry!.entries.map((e) => MapEntry(e.key, e.value.toString())));
    }
    if (tool?.idempotency != null) {
      _idempotencyConfig.addAll(tool!.idempotency!.entries.map((e) => MapEntry(e.key, e.value.toString())));
    }
    
    // Auto-generate ID from name
    _nameController.addListener(_updateIdFromName);
  }

  void _updateIdFromName() {
    if (widget.editTool != null) return;
    
    final name = _nameController.text;
    var id = name.toLowerCase().trim();
    id = id.replaceAll(RegExp(r'\s+'), '-');
    id = id.replaceAll(RegExp(r'[^a-z0-9-]'), '');
    id = id.replaceAll(RegExp(r'-+'), '-');
    if (id.startsWith('-')) id = id.substring(1);
    if (id.endsWith('-')) id = id.substring(0, id.length - 1);
    if (id.isEmpty) id = 'tool';
    id = '$id-v1';
    
    _idController.text = id;
  }

  String _getDefaultCode() {
    return '''async def my_function(args: dict) -> dict:
    """
    Tool function implementation.
    
    Args:
        args: Dictionary of input parameters
        
    Returns:
        Dictionary with result data
    """
    # TODO: Implement your logic here
    return {"result": "success"}
''';
  }

  @override
  void dispose() {
    _nameController.removeListener(_updateIdFromName);
    _idController.dispose();
    _nameController.dispose();
    _descriptionController.dispose();
    _versionController.dispose();
    _urlController.dispose();
    _codeController.dispose();
    _hostController.dispose();
    _portController.dispose();
    _databaseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppTheme.surfaceDark,
      borderRadius: BorderRadius.circular(16),
      child: Column(
        children: [
          _buildHeader(),
          _buildStepIndicator(),
          Expanded(
            child: Form(
              key: _formKey,
              child: _buildCurrentStep(),
            ),
          ),
          _buildFooter(),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.dividerDark)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [AppTheme.primary, AppTheme.primary.withOpacity(0.8)]),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              widget.editTool != null ? Icons.edit : Icons.add,
              color: Colors.white,
              size: 22,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.editTool != null ? 'Edit Tool' : 'Create New Tool',
                  style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.textSecondaryDark),
                ),
                const SizedBox(height: 2),
                Text(
                  _getStepDescription(),
                  style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w400, color: AppTheme.textSecondaryDark),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.close),
            color: AppTheme.textTertiaryDark,
          ),
        ],
      ),
    );
  }

  String _getStepDescription() {
    switch (_currentStep) {
      case 0:
        return 'Select tool type and basic information';
      case 1:
        return 'Configure ${_toolType} specific settings';
      case 2:
        return 'Define input parameters';
      case 3:
        return 'Execution and advanced settings';
      default:
        return '';
    }
  }

  Widget _buildStepIndicator() {
    final steps = ['Type & Info', 'Configuration', 'Parameters', 'Settings'];
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        children: List.generate(steps.length, (index) {
          final isActive = index == _currentStep;
          final isCompleted = index < _currentStep;
          
          return Expanded(
            child: Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: isActive || isCompleted
                        ? AppTheme.primary
                        : AppTheme.surfaceDark,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isActive || isCompleted
                          ? AppTheme.primary
                          : AppTheme.dividerDark,
                    ),
                  ),
                  child: Center(
                    child: isCompleted
                        ? const Icon(Icons.check, size: 16, color: Colors.white)
                        : Text(
                            '${index + 1}',
                            style: GoogleFonts.inter(
                              color: isActive ? Colors.white : AppTheme.textTertiaryDark,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    steps[index],
                    style: GoogleFonts.inter(
                      color: isActive ? AppTheme.textPrimaryDark : AppTheme.textTertiaryDark,
                      fontSize: 13,
                      fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (index < steps.length - 1)
                  Expanded(
                    child: Container(
                      height: 1,
                      margin: const EdgeInsets.symmetric(horizontal: 8),
                      color: isCompleted ? AppTheme.primary : AppTheme.dividerDark,
                    ),
                  ),
              ],
            ),
          );
        }),
      ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case 0:
        return _buildStep1TypeAndInfo();
      case 1:
        return _buildStep2Configuration();
      case 2:
        return _buildStep3Parameters();
      case 3:
        return _buildStep4Settings();
      default:
        return const SizedBox();
    }
  }

  Widget _buildStep1TypeAndInfo() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Tool Type Selection
          Text('Tool Type', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildTypeCard(
                type: 'function',
                label: 'Function',
                description: 'Python code',
                icon: Icons.code,
                color: AppTheme.functionColor,
              ),
              const SizedBox(width: 12),
              _buildTypeCard(
                type: 'http',
                label: 'HTTP',
                description: 'REST API',
                icon: Icons.http,
                color: AppTheme.httpColor,
              ),
              const SizedBox(width: 12),
              _buildTypeCard(
                type: 'db',
                label: 'Database',
                description: 'SQL query',
                icon: Icons.storage,
                color: AppTheme.dbColor,
              ),
            ],
          ),
          
          const SizedBox(height: 32),
          
          // Basic Info
          Text('Basic Information', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
          const SizedBox(height: 16),
          
          TextFormField(
            controller: _nameController,
            decoration: const InputDecoration(
              labelText: 'Display Name',
              hintText: 'My Tool',
              helperText: 'Human-readable name for this tool',
            ),
            validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          
          TextFormField(
            controller: _idController,
            decoration: const InputDecoration(
              labelText: 'Tool ID',
              hintText: 'my-tool-v1',
              helperText: 'Unique identifier (auto-generated from name)',
            ),
            validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          
          TextFormField(
            controller: _descriptionController,
            decoration: const InputDecoration(
              labelText: 'Description',
              hintText: 'Describe what this tool does...',
              helperText: 'Helps the LLM understand when to use this tool',
            ),
            maxLines: 3,
            validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          
          TextFormField(
            controller: _versionController,
            decoration: const InputDecoration(
              labelText: 'Version',
              hintText: '1.0.0',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypeCard({
    required String type,
    required String label,
    required String description,
    required IconData icon,
    required Color color,
  }) {
    final isSelected = _toolType == type;
    
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _toolType = type),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isSelected ? color.withOpacity(0.1) : AppTheme.surfaceDark,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? color : AppTheme.dividerDark,
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Column(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: color, size: 22),
              ),
              const SizedBox(height: 10),
              Text(
                label,
                style: GoogleFonts.inter(
                  color: isSelected ? color : AppTheme.textPrimaryDark,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(description, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStep2Configuration() {
    switch (_toolType) {
      case 'http':
        return _buildHttpConfig();
      case 'function':
        return _buildFunctionConfig();
      case 'db':
        return _buildDbConfig();
      default:
        return const SizedBox();
    }
  }

  Widget _buildHttpConfig() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('HTTP Configuration', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
          const SizedBox(height: 16),
          
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 120,
                child: DropdownButtonFormField<String>(
                  value: _method,
                  decoration: const InputDecoration(labelText: 'Method'),
                  items: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
                      .map((m) => DropdownMenuItem(value: m, child: Text(m)))
                      .toList(),
                  onChanged: (v) => setState(() => _method = v!),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextFormField(
                  controller: _urlController,
                  decoration: const InputDecoration(
                    labelText: 'URL',
                    hintText: 'https://api.example.com/endpoint',
                  ),
                  validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          
          Row(
            children: [
              Text('Headers', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
              const Spacer(),
              TextButton.icon(
                onPressed: () => setState(() => _headers.add(const MapEntry('', ''))),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add Header'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          if (_headers.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.dividerDark),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.info_outline, size: 16, color: AppTheme.textTertiaryDark),
                  const SizedBox(width: 8),
                  Text('No headers configured', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark)),
                ],
              ),
            )
          else
            ...List.generate(_headers.length, (i) => _buildHeaderRow(i)),
        ],
      ),
    );
  }

  Widget _buildHeaderRow(int index) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Header name',
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              onChanged: (v) => _headers[index] = MapEntry(v, _headers[index].value),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 2,
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Value',
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              onChanged: (v) => _headers[index] = MapEntry(_headers[index].key, v),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: () => setState(() => _headers.removeAt(index)),
            icon: const Icon(Icons.delete_outline, size: 18),
            color: AppTheme.error,
          ),
        ],
      ),
    );
  }

  Widget _buildFunctionConfig() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Function Code', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
          const SizedBox(height: 8),
          Text(
            'Write your async Python function. Receives args dict, returns result dict.',
            style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark),
          ),
          const SizedBox(height: 16),
          
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF1E1E1E),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.dividerDark),
              ),
              child: TextField(
                controller: _codeController,
                maxLines: null,
                expands: true,
                decoration: const InputDecoration(
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.all(16),
                ),
                style: GoogleFonts.firaCode(
                  color: const Color(0xFFD4D4D4),
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDbConfig() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Database Configuration', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
          const SizedBox(height: 16),
          
          DropdownButtonFormField<String>(
            value: _driver,
            decoration: const InputDecoration(labelText: 'Database Driver'),
            items: ['postgresql', 'mysql', 'sqlite', 'dynamodb', 'mongodb']
                .map((d) => DropdownMenuItem(value: d, child: Text(d)))
                .toList(),
            onChanged: (v) {
              setState(() {
                _driver = v!;
                // Update default port
                switch (v) {
                  case 'postgresql':
                    _portController.text = '5432';
                    break;
                  case 'mysql':
                    _portController.text = '3306';
                    break;
                  case 'mongodb':
                    _portController.text = '27017';
                    break;
                }
              });
            },
          ),
          const SizedBox(height: 16),
          
          Row(
            children: [
              Expanded(
                flex: 2,
                child: TextFormField(
                  controller: _hostController,
                  decoration: const InputDecoration(
                    labelText: 'Host',
                    hintText: 'localhost',
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: TextFormField(
                  controller: _portController,
                  decoration: const InputDecoration(
                    labelText: 'Port',
                  ),
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          TextFormField(
            controller: _databaseController,
            decoration: const InputDecoration(
              labelText: 'Database Name',
              hintText: 'mydb',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStep3Parameters() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text('Parameters', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
              const Spacer(),
              ElevatedButton.icon(
                onPressed: _addParameter,
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Add Parameter'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Define the input parameters for your tool',
            style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark),
          ),
          const SizedBox(height: 16),
          
          if (_parameters.isEmpty)
            Container(
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                color: AppTheme.surfaceDark,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.dividerDark),
              ),
              child: Column(
                children: [
                  Icon(
                    Icons.input,
                    size: 40,
                    color: AppTheme.textTertiaryDark.withOpacity(0.5),
                  ),
                  const SizedBox(height: 12),
                  Text('No parameters defined', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w400, color: AppTheme.textSecondaryDark)),
                  const SizedBox(height: 4),
                  Text(
                    'Click "Add Parameter" to define inputs',
                    style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark),
                  ),
                ],
              ),
            )
          else
            ...List.generate(_parameters.length, (i) => _buildParameterCard(i)),
        ],
      ),
    );
  }

  Widget _buildParameterCard(int index) {
    final param = _parameters[index];
    
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.surfaceDark,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.dividerDark),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  param.type,
                  style: GoogleFonts.firaCode(
                    color: AppTheme.primary,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                param.name,
                style: GoogleFonts.firaCode(
                  color: AppTheme.textPrimaryDark,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (param.required) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.error.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'required',
                    style: GoogleFonts.inter(
                      color: AppTheme.error,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
              const Spacer(),
              IconButton(
                onPressed: () => _editParameter(index),
                icon: const Icon(Icons.edit_outlined, size: 18),
                color: AppTheme.textTertiaryDark,
              ),
              IconButton(
                onPressed: () => setState(() => _parameters.removeAt(index)),
                icon: const Icon(Icons.delete_outline, size: 18),
                color: AppTheme.error,
              ),
            ],
          ),
          if (param.description.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(param.description, style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark)),
          ],
        ],
      ),
    );
  }

  Widget _buildStep4Settings() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Execution Settings', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
          const SizedBox(height: 16),
          
          // Timeout slider
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Timeout (seconds)', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.textSecondaryDark)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: Slider(
                            value: _timeoutS.toDouble(),
                            min: 5,
                            max: 300,
                            divisions: 59,
                            onChanged: (v) => setState(() => _timeoutS = v.round()),
                          ),
                        ),
                        SizedBox(
                          width: 50,
                          child: Text(
                            '${_timeoutS}s',
                            style: GoogleFonts.firaCode(
                              color: AppTheme.textPrimaryDark,
                              fontSize: 14,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 24),
          
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Return Type', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.textSecondaryDark)),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: _returnType,
                      items: ['json', 'text']
                          .map((t) => DropdownMenuItem(
                                value: t,
                                child: Text(t.toUpperCase()),
                              ))
                          .toList(),
                      onChanged: (v) => setState(() => _returnType = v!),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Return Target', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.textSecondaryDark)),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: _returnTarget,
                      items: [
                        const DropdownMenuItem(value: 'llm', child: Text('LLM')),
                        const DropdownMenuItem(value: 'human', child: Text('Human')),
                        const DropdownMenuItem(value: 'agent', child: Text('Agent')),
                        const DropdownMenuItem(value: 'step', child: Text('Step')),
                      ],
                      onChanged: (v) => setState(() => _returnTarget = v!),
                    ),
                  ],
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 32),
          
          // Retry Configuration
          _buildKeyValueSection(
            title: 'Retry Configuration',
            items: _retryConfig,
            onAdd: () => setState(() => _retryConfig.add(const MapEntry('', ''))),
            onRemove: (index) => setState(() => _retryConfig.removeAt(index)),
            onUpdate: (index, key, value) => setState(() => _retryConfig[index] = MapEntry(key, value)),
          ),
          
          const SizedBox(height: 24),
          
          // Idempotency Configuration
          _buildKeyValueSection(
            title: 'Idempotency Configuration',
            items: _idempotencyConfig,
            onAdd: () => setState(() => _idempotencyConfig.add(const MapEntry('', ''))),
            onRemove: (index) => setState(() => _idempotencyConfig.removeAt(index)),
            onUpdate: (index, key, value) => setState(() => _idempotencyConfig[index] = MapEntry(key, value)),
          ),
          
          const SizedBox(height: 32),
          
          // Summary card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.primary.withOpacity(0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.primary.withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Summary', style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
                const SizedBox(height: 12),
                _buildSummaryRow('Type', _toolType.toUpperCase()),
                _buildSummaryRow('Name', _nameController.text),
                _buildSummaryRow('ID', _idController.text),
                _buildSummaryRow('Parameters', '${_parameters.length}'),
                _buildSummaryRow('Timeout', '${_timeoutS}s'),
                if (_retryConfig.isNotEmpty) _buildSummaryRow('Retry', 'Configured'),
                if (_idempotencyConfig.isNotEmpty) _buildSummaryRow('Idempotency', 'Configured'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.textSecondaryDark)),
          ),
          Expanded(
            child: Text(value, style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark)),
          ),
        ],
      ),
    );
  }

  Widget _buildFooter() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppTheme.dividerDark)),
      ),
      child: Row(
        children: [
          if (_currentStep > 0)
            OutlinedButton(
              onPressed: () => setState(() => _currentStep--),
              child: const Text('Back'),
            ),
          const Spacer(),
          if (_currentStep < 3)
            ElevatedButton(
              onPressed: _nextStep,
              child: const Text('Continue'),
            )
          else
            ElevatedButton(
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(widget.editTool != null ? 'Save Changes' : 'Create Tool'),
            ),
        ],
      ),
    );
  }

  void _nextStep() {
    if (_currentStep == 0 && !_formKey.currentState!.validate()) return;
    setState(() => _currentStep++);
  }

  void _addParameter() {
    _showParameterDialog(null);
  }

  void _editParameter(int index) {
    _showParameterDialog(_parameters[index], index);
  }

  void _showParameterDialog(ToolParameter? param, [int? index]) {
    final nameController = TextEditingController(text: param?.name ?? '');
    final descController = TextEditingController(text: param?.description ?? '');
    String type = param?.type ?? 'string';
    bool required = param?.required ?? false;
    
    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(param != null ? 'Edit Parameter' : 'Add Parameter'),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: nameController,
                  decoration: const InputDecoration(
                    labelText: 'Name',
                    hintText: 'parameter_name',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: descController,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    hintText: 'What this parameter is for',
                  ),
                  maxLines: 2,
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: type,
                        decoration: const InputDecoration(labelText: 'Type'),
                        items: ['string', 'number', 'integer', 'boolean', 'array', 'object']
                            .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                            .toList(),
                        onChanged: (v) => setDialogState(() => type = v!),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Required', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.textSecondaryDark)),
                        const SizedBox(height: 8),
                        Switch(
                          value: required,
                          onChanged: (v) => setDialogState(() => required = v),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                if (nameController.text.isNotEmpty) {
                  final newParam = ToolParameter(
                    name: nameController.text,
                    description: descController.text,
                    type: type,
                    required: required,
                  );
                  
                  setState(() {
                    if (index != null) {
                      _parameters[index] = newParam;
                    } else {
                      _parameters.add(newParam);
                    }
                  });
                  Navigator.of(context).pop();
                }
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      setState(() => _currentStep = 0);
      return;
    }
    
    setState(() => _isSubmitting = true);
    
    final tool = Tool(
      id: _idController.text,
      toolName: _nameController.text,
      description: _descriptionController.text,
      toolType: _toolType,
      version: _versionController.text,
      parameters: _parameters,
      timeoutS: _timeoutS,
      returnType: _returnType,
      returnTarget: _returnTarget,
      url: _toolType == 'http' ? _urlController.text : null,
      method: _toolType == 'http' ? _method : null,
      headers: _toolType == 'http' && _headers.isNotEmpty
          ? Map.fromEntries(_headers.where((e) => e.key.isNotEmpty))
          : null,
      functionCode: _toolType == 'function' ? _codeController.text : null,
      driver: _toolType == 'db' ? _driver : null,
      host: _toolType == 'db' ? _hostController.text : null,
      port: _toolType == 'db' ? int.tryParse(_portController.text) : null,
      database: _toolType == 'db' ? _databaseController.text : null,
      retry: _retryConfig.isNotEmpty
          ? Map.fromEntries(_retryConfig.where((e) => e.key.isNotEmpty).map((e) {
              // Try to parse booleans and numbers
              dynamic value = e.value;
              if (value.toLowerCase() == 'true') value = true;
              else if (value.toLowerCase() == 'false') value = false;
              else if (int.tryParse(value) != null) value = int.parse(value);
              else if (double.tryParse(value) != null) value = double.parse(value);
              return MapEntry(e.key, value);
            }))
          : null,
      idempotency: _idempotencyConfig.isNotEmpty
          ? Map.fromEntries(_idempotencyConfig.where((e) => e.key.isNotEmpty).map((e) {
              dynamic value = e.value;
              if (value.toLowerCase() == 'true') value = true;
              else if (value.toLowerCase() == 'false') value = false;
              return MapEntry(e.key, value);
            }))
          : null,
    );
    
    final provider = context.read<ToolsProvider>();
    final result = widget.editTool != null
        ? await provider.updateTool(tool)
        : await provider.createTool(tool);
    
    setState(() => _isSubmitting = false);
    
    if (mounted) {
      if (result['success']) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: AppTheme.success,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: AppTheme.error,
          ),
        );
      }
    }
  }
  Widget _buildKeyValueSection({
    required String title,
    required List<MapEntry<String, String>> items,
    required VoidCallback onAdd,
    required Function(int) onRemove,
    required Function(int, String, String) onUpdate,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(title, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
            const Spacer(),
            TextButton.icon(
              onPressed: onAdd,
              icon: const Icon(Icons.add, size: 16),
              label: const Text('Add Item'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (items.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppTheme.surfaceDark,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.dividerDark),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.info_outline, size: 16, color: AppTheme.textTertiaryDark),
                const SizedBox(width: 8),
                Text('Not configured', style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark)),
              ],
            ),
          )
        else
          ...List.generate(items.length, (i) {
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      initialValue: items[i].key,
                      decoration: const InputDecoration(
                        hintText: 'Key',
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      onChanged: (v) => onUpdate(i, v, items[i].value),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    flex: 2,
                    child: TextFormField(
                      initialValue: items[i].value,
                      decoration: const InputDecoration(
                        hintText: 'Value',
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      onChanged: (v) => onUpdate(i, items[i].key, v),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () => onRemove(i),
                    icon: const Icon(Icons.delete_outline, size: 18),
                    color: AppTheme.error,
                  ),
                ],
              ),
            );
          }),
      ],
    );
  }
}


