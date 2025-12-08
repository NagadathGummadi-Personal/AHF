import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../models/tool.dart';
import '../providers/tools_provider.dart';
import '../theme/app_theme.dart';

class CreateToolDialog extends StatefulWidget {
  final ToolType? initialType;
  final Tool? editTool;

  const CreateToolDialog({super.key, this.initialType, this.editTool});

  @override
  State<CreateToolDialog> createState() => _CreateToolDialogState();
}

class _CreateToolDialogState extends State<CreateToolDialog> {
  final _formKey = GlobalKey<FormState>();
  int _currentStep = 0;
  late ToolType _selectedType;
  
  // Basic info
  final _idController = TextEditingController();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  
  // HTTP specific
  final _urlController = TextEditingController();
  String _selectedMethod = 'POST';
  final List<MapEntry<String, String>> _headers = [];
  
  // Function specific
  final _codeController = TextEditingController();
  
  // DB specific
  String _selectedDriver = 'postgresql';
  final _hostController = TextEditingController(text: 'localhost');
  final _portController = TextEditingController(text: '5432');
  final _databaseController = TextEditingController();
  
  // Parameters
  final List<ToolParameter> _parameters = [];
  
  // Config
  int _timeoutSeconds = 30;
  ToolReturnType _returnType = ToolReturnType.json;
  ToolReturnTarget _returnTarget = ToolReturnTarget.llm;
  bool _retryEnabled = false;
  int _maxRetries = 3;
  bool _idempotencyEnabled = false;
  int _idempotencyTtl = 3600;
  String _idempotencyKeys = '';
  bool _idempotencyBypass = false;
  final _dynamicVarsController = TextEditingController();
  final _securityController = TextEditingController();
  final _validationController = TextEditingController();
  
  bool _isCreating = false;

  @override
  void initState() {
    super.initState();
    _selectedType = widget.initialType ?? ToolType.function;
    
    if (widget.editTool != null) {
      _loadToolData(widget.editTool!);
    } else {
      _updateGeneratedId();
      _updateCodeTemplate();
    }
    
    // Listen to name changes to update code template and generated id
    _nameController.addListener(() {
      _updateGeneratedId();
      _updateCodeTemplate();
    });
  }

  void _loadToolData(Tool tool) {
    _idController.text = tool.id;
    _nameController.text = tool.name;
    _descriptionController.text = tool.description;
    _selectedType = tool.type;
    _timeoutSeconds = tool.timeoutSeconds;
    _returnType = tool.returnType;
    _returnTarget = tool.returnTarget;
    _parameters.addAll(tool.parameters);
    _retryEnabled = tool.retry.enabled;
    _maxRetries = tool.retry.maxRetries;
    _idempotencyEnabled = tool.idempotency.enabled;
    _idempotencyTtl = tool.idempotency.ttlSeconds;
    _idempotencyKeys = tool.idempotency.keyFields.join(', ');
    _idempotencyBypass = tool.idempotency.bypassOnMissingKey;
    if (tool.dynamicVariables != null) {
      _dynamicVarsController.text = jsonEncode(tool.dynamicVariables);
    }
    if (tool.security != null) {
      _securityController.text = jsonEncode(tool.security);
    }
    if (tool.validation != null) {
      _validationController.text = jsonEncode(tool.validation);
    }
    
    if (tool.type == ToolType.http) {
      _urlController.text = tool.url ?? '';
      _selectedMethod = tool.method ?? 'POST';
      if (tool.headers != null) {
        _headers.addAll(tool.headers!.entries);
      }
    } else if (tool.type == ToolType.function) {
      _codeController.text = tool.functionCode ?? '';
    } else if (tool.type == ToolType.db) {
      _selectedDriver = tool.driver ?? 'postgresql';
      _hostController.text = tool.host ?? 'localhost';
      _portController.text = (tool.port ?? 5432).toString();
      _databaseController.text = tool.database ?? '';
    }
  }

  void _updateCodeTemplate() {
    if (_selectedType == ToolType.function && _codeController.text.isEmpty || 
        _codeController.text.startsWith('from typing import')) {
      final funcName = _toSnakeCase(_nameController.text.isEmpty ? 'my_function' : _nameController.text);
      final provider = context.read<ToolsProvider>();
      _codeController.text = provider.generateFunctionTemplate(funcName, _parameters);
    }
  }

  String _generateIdFromName(String name) {
    var slug = name.toLowerCase().trim();
    slug = slug.replaceAll(RegExp(r'\s+'), '-');
    slug = slug.replaceAll(RegExp(r'[^a-z0-9-]'), '');
    slug = slug.replaceAll(RegExp(r'-+'), '-');
    if (slug.startsWith('-')) slug = slug.replaceFirst(RegExp(r'^-+'), '');
    if (slug.endsWith('-')) slug = slug.replaceFirst(RegExp(r'-+$'), '');
    if (slug.isEmpty) slug = 'tool';
    return slug;
  }

  void _updateGeneratedId() {
    if (widget.editTool != null) return; // Keep existing id on edit
    _idController.text = _generateIdFromName(_nameController.text.isEmpty ? 'tool' : _nameController.text);
  }

  String _toSnakeCase(String text) {
    return text
        .replaceAllMapped(RegExp(r'[A-Z]'), (m) => '_${m.group(0)!.toLowerCase()}')
        .replaceAll(RegExp(r'[^a-z0-9_]'), '_')
        .replaceAll(RegExp(r'_+'), '_')
        .replaceFirst(RegExp(r'^_'), '');
  }

  Widget _buildCodeEditor() {
    return Container(
      height: 360,
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: const BoxDecoration(
              color: Color(0xFF252526),
              borderRadius: BorderRadius.vertical(top: Radius.circular(7)),
            ),
            child: Row(
              children: [
                const Icon(Icons.code, size: 16, color: Color(0xFF22D3EE)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${_toSnakeCase(_nameController.text.isEmpty ? 'my_function' : _nameController.text)}.py',
                    style: GoogleFonts.firaCode(color: AppTheme.textSecondary, fontSize: 12),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                IconButton(
                  tooltip: 'Regenerate from name & params',
                  icon: const Icon(Icons.refresh, size: 16, color: Colors.white),
                  onPressed: () {
                    final funcName = _toSnakeCase(_nameController.text.isEmpty ? 'my_function' : _nameController.text);
                    final provider = context.read<ToolsProvider>();
                    setState(() {
                      _codeController.text = provider.generateFunctionTemplate(funcName, _parameters);
                    });
                  },
                ),
                IconButton(
                  tooltip: 'Copy code',
                  icon: const Icon(Icons.copy, size: 16, color: Colors.white),
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: _codeController.text));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Code copied')),
                    );
                  },
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: TextField(
                controller: _codeController,
                maxLines: null,
                expands: true,
                decoration: const InputDecoration(
                  filled: true,
                  fillColor: Color(0xFF1E1E1E),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.all(12),
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

  List<TextSpan> _pythonHighlight(String code) {
    final spans = <TextSpan>[];
    final pattern = RegExp(
        r"(#.*$|\""\"[\\s\\S]*?\"\\\"\"|'''[\\s\\S]*?'''|\"[^\"]*\"|'[^']*'|\\b(def|async|await|return|if|else|elif|for|while|in|import|from|as|with|try|except|raise|class|pass|yield|lambda|True|False|None)\\b)",
        multiLine: true);
    int lastIndex = 0;
    const keywordColor = Color(0xFF89DDFF); // cyan-ish
    const stringColor = Color(0xFFB5CEA8); // green
    const commentColor = Color(0xFF6A9955); // muted green

    for (final match in pattern.allMatches(code)) {
      if (match.start > lastIndex) {
        spans.add(TextSpan(text: code.substring(lastIndex, match.start)));
      }
      final text = match.group(0)!;
      TextStyle style = const TextStyle(color: keywordColor);
      if (text.startsWith('#')) {
        style = const TextStyle(color: commentColor);
      } else if (text.startsWith('"') || text.startsWith("'")) {
        style = const TextStyle(color: stringColor);
      }
      spans.add(TextSpan(text: text, style: style));
      lastIndex = match.end;
    }
    if (lastIndex < code.length) {
      spans.add(TextSpan(text: code.substring(lastIndex)));
    }
    return spans;
  }

  @override
  void dispose() {
    _idController.dispose();
    _nameController.dispose();
    _descriptionController.dispose();
    _urlController.dispose();
    _codeController.dispose();
    _hostController.dispose();
    _portController.dispose();
    _databaseController.dispose();
    _dynamicVarsController.dispose();
    _securityController.dispose();
    _validationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: Column(
        children: [
          _buildHeader(),
          _buildStepIndicator(),
          Expanded(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1024),
                child: Form(
                  key: _formKey,
                  child: _buildCurrentStep(),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1024),
              child: _buildFooter(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.borderColor)),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              gradient: AppTheme.primaryGradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              widget.editTool != null ? Icons.edit : Icons.add,
              color: Colors.white,
              size: 24,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.editTool != null ? 'Edit Tool' : 'Create New Tool',
                  style: GoogleFonts.inter(
                    color: AppTheme.textPrimary,
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _getStepDescription(),
                  style: GoogleFonts.inter(
                    color: AppTheme.textTertiary,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.close),
            color: AppTheme.textTertiary,
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
        return 'Configure ${_selectedType.name} specific settings';
      case 2:
        return 'Define input parameters';
      case 3:
        return 'Advanced configuration';
      default:
        return '';
    }
  }

  Widget _buildStepIndicator() {
    final steps = ['Type & Info', 'Configuration', 'Parameters', 'Advanced'];
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
                        ? AppTheme.primaryColor 
                        : AppTheme.surfaceColor,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: isActive || isCompleted 
                          ? AppTheme.primaryColor 
                          : AppTheme.borderColor,
                    ),
                  ),
                  child: Center(
                    child: isCompleted
                        ? const Icon(Icons.check, size: 16, color: Colors.white)
                        : Text(
                            '${index + 1}',
                            style: GoogleFonts.inter(
                              color: isActive ? Colors.white : AppTheme.textTertiary,
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    steps[index],
                    style: GoogleFonts.inter(
                      color: isActive ? AppTheme.textPrimary : AppTheme.textTertiary,
                      fontSize: 13,
                      fontWeight: isActive ? FontWeight.w500 : FontWeight.w400,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (index < steps.length - 1)
                  Expanded(
                    child: Container(
                      height: 1,
                      margin: const EdgeInsets.symmetric(horizontal: 8),
                      color: isCompleted ? AppTheme.primaryColor : AppTheme.borderColor,
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
        return _buildStep4Advanced();
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
          _buildSectionTitle('Tool Type'),
          const SizedBox(height: 12),
          Row(
            children: [
              _TypeCard(
                icon: Icons.code,
                label: 'Function',
                description: 'Python function',
                color: const Color(0xFF22D3EE),
                isSelected: _selectedType == ToolType.function,
                onTap: () => setState(() {
                  _selectedType = ToolType.function;
                  _updateCodeTemplate();
                }),
              ),
              const SizedBox(width: 12),
              _TypeCard(
                icon: Icons.http,
                label: 'HTTP',
                description: 'REST API call',
                color: const Color(0xFFA78BFA),
                isSelected: _selectedType == ToolType.http,
                onTap: () => setState(() => _selectedType = ToolType.http),
              ),
              const SizedBox(width: 12),
              _TypeCard(
                icon: Icons.storage,
                label: 'Database',
                description: 'SQL query',
                color: const Color(0xFFFBBF24),
                isSelected: _selectedType == ToolType.db,
                onTap: () => setState(() => _selectedType = ToolType.db),
              ),
            ],
          ),
          const SizedBox(height: 32),
          
          _buildSectionTitle('Basic Information'),
          const SizedBox(height: 16),
          
          _buildTextField(
            controller: _nameController,
            label: 'Display Name',
            hint: 'My Tool',
            helperText: 'ID auto-generated from this name (lowercase + hyphens only)',
            validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
          ),
          const SizedBox(height: 16),
          
          _buildTextField(
            controller: _descriptionController,
            label: 'Description',
            hint: 'Describe what this tool does and when to use it...',
            helperText: 'This helps the AI understand when to use this tool',
            maxLines: 3,
            validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
          ),
        ],
      ),
    );
  }

  Widget _buildStep2Configuration() {
    switch (_selectedType) {
      case ToolType.function:
        return _buildFunctionConfigBasic();
      case ToolType.http:
        return _buildHttpConfig();
      case ToolType.db:
        return _buildDbConfig();
    }
  }

  Widget _buildFunctionConfigBasic() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle('Function Configuration'),
          const SizedBox(height: 8),
          Text(
            'Define parameters next. Python code will be generated after parameters.',
            style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildHttpConfig() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle('HTTP Configuration'),
          const SizedBox(height: 16),
          
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 120,
                child: _buildDropdown(
                  label: 'Method',
                  value: _selectedMethod,
                  items: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
                  onChanged: (v) => setState(() => _selectedMethod = v!),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildTextField(
                  controller: _urlController,
                  label: 'URL',
                  hint: 'https://api.example.com/endpoint',
                  validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          
          Row(
            children: [
              _buildSectionTitle('Headers'),
              const Spacer(),
              TextButton.icon(
                onPressed: () => setState(() => _headers.add(const MapEntry('', ''))),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add Header'),
                style: TextButton.styleFrom(foregroundColor: AppTheme.primaryColor),
              ),
            ],
          ),
          const SizedBox(height: 12),
          
          if (_headers.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceColor,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.info_outline, size: 16, color: AppTheme.textTertiary),
                  const SizedBox(width: 8),
                  Text(
                    'No headers configured',
                    style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
                  ),
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
                filled: true,
                fillColor: AppTheme.surfaceColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              style: GoogleFonts.firaCode(color: AppTheme.textPrimary, fontSize: 13),
              onChanged: (v) => _headers[index] = MapEntry(v, _headers[index].value),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 2,
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Value (use \${VAR} for variables)',
                filled: true,
                fillColor: AppTheme.surfaceColor,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppTheme.borderColor),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              ),
              style: GoogleFonts.firaCode(color: AppTheme.textPrimary, fontSize: 13),
              onChanged: (v) => _headers[index] = MapEntry(_headers[index].key, v),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: () => setState(() => _headers.removeAt(index)),
            icon: const Icon(Icons.delete_outline, size: 18),
            color: AppTheme.errorColor,
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
          _buildSectionTitle('Database Configuration'),
          const SizedBox(height: 16),
          
          _buildDropdown(
            label: 'Database Driver',
            value: _selectedDriver,
            items: ['postgresql', 'mysql', 'sqlite', 'mssql', 'mongodb'],
            onChanged: (v) => setState(() {
              _selectedDriver = v!;
              if (v == 'postgresql') _portController.text = '5432';
              if (v == 'mysql') _portController.text = '3306';
              if (v == 'mssql') _portController.text = '1433';
              if (v == 'mongodb') _portController.text = '27017';
            }),
          ),
          const SizedBox(height: 16),
          
          Row(
            children: [
              Expanded(
                flex: 2,
                child: _buildTextField(
                  controller: _hostController,
                  label: 'Host',
                  hint: 'localhost',
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildTextField(
                  controller: _portController,
                  label: 'Port',
                  hint: '5432',
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          _buildTextField(
            controller: _databaseController,
            label: 'Database Name',
            hint: 'mydb',
            validator: (v) => v?.isEmpty ?? true ? 'Required' : null,
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
              _buildSectionTitle('Input Parameters'),
              const Spacer(),
              TextButton.icon(
                onPressed: _addParameter,
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add Parameter'),
                style: TextButton.styleFrom(foregroundColor: AppTheme.primaryColor),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Define the parameters your tool accepts',
            style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
          ),
          const SizedBox(height: 16),
          
          if (_parameters.isEmpty)
            Container(
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                color: AppTheme.surfaceColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: Column(
                children: [
                  Icon(Icons.input, size: 40, color: AppTheme.textTertiary.withOpacity(0.5)),
                  const SizedBox(height: 12),
                  Text(
                    'No parameters defined',
                    style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 14),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Click "Add Parameter" to define inputs for your tool',
                    style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
                  ),
                ],
              ),
            )
          else
            ...List.generate(_parameters.length, (i) => _buildParameterCard(i)),

          if (_selectedType == ToolType.function) ...[
            const SizedBox(height: 24),
            _buildSectionTitle('Function Code'),
            const SizedBox(height: 8),
            Text(
              'Python async function. Uses args dict. Code regenerated when name/params change.',
              style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
            ),
            const SizedBox(height: 12),
            _buildCodeEditor(),
          ],
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
        color: AppTheme.cardColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.primaryColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  param.type,
                  style: GoogleFonts.firaCode(
                    color: AppTheme.primaryColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                param.name,
                style: GoogleFonts.firaCode(
                  color: AppTheme.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              if (param.required) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.errorColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'required',
                    style: GoogleFonts.inter(
                      color: AppTheme.errorColor,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
              const Spacer(),
              IconButton(
                onPressed: () => _editParameter(index),
                icon: const Icon(Icons.edit_outlined, size: 18),
                color: AppTheme.textTertiary,
              ),
              IconButton(
                onPressed: () => setState(() {
                  _parameters.removeAt(index);
                  _updateCodeTemplate();
                }),
                icon: const Icon(Icons.delete_outline, size: 18),
                color: AppTheme.errorColor,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            param.description,
            style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildStep4Advanced() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionTitle('Execution Settings'),
          const SizedBox(height: 16),
          
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Timeout (seconds)', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: Slider(
                            value: _timeoutSeconds.toDouble(),
                            min: 5,
                            max: 120,
                            divisions: 23,
                            activeColor: AppTheme.primaryColor,
                            onChanged: (v) => setState(() => _timeoutSeconds = v.round()),
                          ),
                        ),
                        SizedBox(
                          width: 50,
                          child: Text(
                            '${_timeoutSeconds}s',
                            style: GoogleFonts.firaCode(color: AppTheme.textPrimary, fontSize: 13),
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
                child: _buildDropdown(
                  label: 'Return Type',
                  value: _returnType.name,
                  items: ['json', 'text'],
                  onChanged: (v) => setState(() => _returnType = ToolReturnType.values.firstWhere((e) => e.name == v)),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _buildDropdown(
                  label: 'Return Target',
                  value: _returnTarget.name,
                  items: ['llm', 'human', 'agent', 'step'],
                  onChanged: (v) => setState(() => _returnTarget = ToolReturnTarget.values.firstWhere((e) => e.name == v)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 32),
          
          _buildSectionTitle('Retry Configuration'),
          const SizedBox(height: 16),
          
          SwitchListTile(
            value: _retryEnabled,
            onChanged: (v) => setState(() => _retryEnabled = v),
            title: Text('Enable Retries', style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14)),
            subtitle: Text('Automatically retry on transient failures', style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 12)),
            activeColor: AppTheme.primaryColor,
            contentPadding: EdgeInsets.zero,
          ),
          
          if (_retryEnabled) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Text('Max Retries:', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
                const SizedBox(width: 16),
                ...List.generate(5, (i) => Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text('${i + 1}'),
                    selected: _maxRetries == i + 1,
                    onSelected: (_) => setState(() => _maxRetries = i + 1),
                    selectedColor: AppTheme.primaryColor,
                    labelStyle: GoogleFonts.inter(
                      color: _maxRetries == i + 1 ? Colors.white : AppTheme.textSecondary,
                    ),
                  ),
                )),
              ],
            ),
          ],

          const SizedBox(height: 32),
          _buildIdempotencySection(),

          const SizedBox(height: 32),
          _buildAdvancedJsonSection(
            title: 'Dynamic Variable Assignments',
            hint: 'Map result fields to variables, e.g. {"order_id": "${_returnTarget == ToolReturnTarget.llm ? 'result' : 'response'}.id"}',
            controller: _dynamicVarsController,
          ),

          const SizedBox(height: 24),
          _buildAdvancedJsonSection(
            title: 'Security Policies',
            hint: 'Define egress/ingress rules or auth context, e.g. {"allow_domains": ["api.myapp.com"]}',
            controller: _securityController,
          ),

          const SizedBox(height: 24),
          _buildAdvancedJsonSection(
            title: 'Validation Rules',
            hint: 'JSON schema or simple rules, e.g. {"required": ["user_id"], "types": {"user_id": "string"}}',
            controller: _validationController,
          ),
        ],
      ),
    );
  }

  Widget _buildIdempotencySection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle('Idempotency'),
        const SizedBox(height: 12),
        SwitchListTile(
          value: _idempotencyEnabled,
          onChanged: (v) => setState(() => _idempotencyEnabled = v),
          title: Text('Enable Idempotency', style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14)),
          subtitle: Text('Cache/guard repeated executions using key fields', style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 12)),
          activeColor: AppTheme.primaryColor,
          contentPadding: EdgeInsets.zero,
        ),
        if (_idempotencyEnabled) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('TTL (seconds)', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextFormField(
                      initialValue: _idempotencyTtl.toString(),
                      keyboardType: TextInputType.number,
                      onChanged: (v) => _idempotencyTtl = int.tryParse(v) ?? _idempotencyTtl,
                      decoration: InputDecoration(
                        hintText: '3600',
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: const BorderSide(color: AppTheme.borderColor),
                        ),
                      ),
                      style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Key Fields (comma separated)', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextFormField(
                      initialValue: _idempotencyKeys,
                      onChanged: (v) => _idempotencyKeys = v,
                      decoration: InputDecoration(
                        hintText: 'user_id, session_id',
                        filled: true,
                        fillColor: Colors.white,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                          borderSide: const BorderSide(color: AppTheme.borderColor),
                        ),
                      ),
                      style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 13),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          CheckboxListTile(
            value: _idempotencyBypass,
            onChanged: (v) => setState(() => _idempotencyBypass = v ?? false),
            title: Text('Bypass when key is missing', style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 13)),
            controlAffinity: ListTileControlAffinity.leading,
            dense: true,
          ),
        ],
      ],
    );
  }

  Widget _buildAdvancedJsonSection({
    required String title,
    required String hint,
    required TextEditingController controller,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionTitle(title),
        const SizedBox(height: 8),
        Text(
          hint,
          style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 12),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          maxLines: 4,
          decoration: InputDecoration(
            hintText: '{ }',
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: AppTheme.borderColor),
            ),
          ),
          style: GoogleFonts.firaCode(color: AppTheme.textPrimary, fontSize: 13),
        ),
      ],
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: GoogleFonts.inter(
        color: AppTheme.textPrimary,
        fontSize: 15,
        fontWeight: FontWeight.w600,
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    String? hint,
    String? helperText,
    int maxLines = 1,
    String? Function(String?)? validator,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
        const SizedBox(height: 8),
        TextFormField(
          controller: controller,
          maxLines: maxLines,
          validator: validator,
          decoration: InputDecoration(
            hintText: hint,
            filled: true,
            fillColor: AppTheme.surfaceColor,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: AppTheme.borderColor),
            ),
          ),
          style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
        ),
        if (helperText != null) ...[
          const SizedBox(height: 4),
          Text(helperText, style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 11)),
        ],
      ],
    );
  }

  Widget _buildDropdown({
    required String label,
    required String value,
    required List<String> items,
    required Function(String?) onChanged,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: AppTheme.surfaceColor,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppTheme.borderColor),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              dropdownColor: AppTheme.cardColor,
              items: items.map((item) => DropdownMenuItem(
                value: item,
                child: Text(item.toUpperCase(), style: GoogleFonts.firaCode(color: AppTheme.textPrimary, fontSize: 13)),
              )).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFooter() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: AppTheme.borderColor)),
      ),
      child: Row(
        children: [
          if (_currentStep > 0)
            OutlinedButton(
              onPressed: () => setState(() => _currentStep--),
              child: const Text('Back'),
            ),
          const Spacer(),
          if (_currentStep < 3) ...[
            ElevatedButton(
              onPressed: _nextStep,
              child: const Text('Continue'),
            ),
          ] else ...[
            ElevatedButton(
              onPressed: _isCreating ? null : _createTool,
              child: _isCreating
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : Text(widget.editTool != null ? 'Save Changes' : 'Create Tool'),
            ),
          ],
        ],
      ),
    );
  }

  void _nextStep() {
    if (_currentStep == 0) {
      if (!_formKey.currentState!.validate()) return;
    }
    if (_currentStep == 1 && _selectedType == ToolType.function) {
      setState(() => _currentStep = 2);
      return;
    }
    setState(() => _currentStep++);
  }

  void _addParameter() {
    showDialog(
      context: context,
      builder: (context) => _ParameterDialog(
        onSave: (param) {
          setState(() {
            _parameters.add(param);
            _updateCodeTemplate();
          });
        },
      ),
    );
  }

  void _editParameter(int index) {
    showDialog(
      context: context,
      builder: (context) => _ParameterDialog(
        parameter: _parameters[index],
        onSave: (param) {
          setState(() {
            _parameters[index] = param;
            _updateCodeTemplate();
          });
        },
      ),
    );
  }

  Future<void> _createTool() async {
    if (!_formKey.currentState!.validate()) {
      setState(() => _currentStep = 0);
      return;
    }

    setState(() => _isCreating = true);

    if (_idController.text.isEmpty) {
      _updateGeneratedId();
    }

    Map<String, dynamic>? _safeDecode(String text) {
      if (text.trim().isEmpty) return null;
      try {
        return jsonDecode(text);
      } catch (_) {
        return null;
      }
    }

    final tool = Tool(
      id: _idController.text,
      name: _nameController.text,
      description: _descriptionController.text,
      type: _selectedType,
      parameters: _parameters,
      timeoutSeconds: _timeoutSeconds,
      returnType: _returnType,
      returnTarget: _returnTarget,
      retry: _retryEnabled ? RetryConfig(enabled: true, maxRetries: _maxRetries) : null,
      idempotency: IdempotencyConfig(
        enabled: _idempotencyEnabled,
        ttlSeconds: _idempotencyTtl,
        keyFields: _idempotencyKeys
            .split(',')
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList(),
        bypassOnMissingKey: _idempotencyBypass,
      ),
      url: _selectedType == ToolType.http ? _urlController.text : null,
      method: _selectedType == ToolType.http ? _selectedMethod : null,
      headers: _selectedType == ToolType.http && _headers.isNotEmpty
          ? Map.fromEntries(_headers.where((e) => e.key.isNotEmpty))
          : null,
      functionCode: _selectedType == ToolType.function ? _codeController.text : null,
      driver: _selectedType == ToolType.db ? _selectedDriver : null,
      host: _selectedType == ToolType.db ? _hostController.text : null,
      port: _selectedType == ToolType.db ? int.tryParse(_portController.text) : null,
      database: _selectedType == ToolType.db ? _databaseController.text : null,
      dynamicVariables: _safeDecode(_dynamicVarsController.text),
      security: _safeDecode(_securityController.text),
      validation: _safeDecode(_validationController.text),
    );

    final provider = context.read<ToolsProvider>();
    final result = widget.editTool != null
        ? await provider.updateTool(tool)
        : await provider.createTool(tool);

    setState(() => _isCreating = false);

    if (mounted) {
      if (result['success']) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: AppTheme.successColor,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: AppTheme.errorColor,
          ),
        );
      }
    }
  }
}

class _TypeCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String description;
  final Color color;
  final bool isSelected;
  final VoidCallback onTap;

  const _TypeCard({
    required this.icon,
    required this.label,
    required this.description,
    required this.color,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: isSelected ? color.withOpacity(0.1) : AppTheme.surfaceColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected ? color : AppTheme.borderColor,
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Column(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color, size: 24),
              ),
              const SizedBox(height: 12),
              Text(
                label,
                style: GoogleFonts.inter(
                  color: isSelected ? color : AppTheme.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: GoogleFonts.inter(
                  color: AppTheme.textTertiary,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ParameterDialog extends StatefulWidget {
  final ToolParameter? parameter;
  final Function(ToolParameter) onSave;

  const _ParameterDialog({this.parameter, required this.onSave});

  @override
  State<_ParameterDialog> createState() => _ParameterDialogState();
}

class _ParameterDialogState extends State<_ParameterDialog> {
  final _nameController = TextEditingController();
  final _descController = TextEditingController();
  String _type = 'string';
  bool _required = true;

  @override
  void initState() {
    super.initState();
    if (widget.parameter != null) {
      _nameController.text = widget.parameter!.name;
      _descController.text = widget.parameter!.description;
      _type = widget.parameter!.type;
      _required = widget.parameter!.required;
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppTheme.cardColor,
      title: Text(
        widget.parameter != null ? 'Edit Parameter' : 'Add Parameter',
        style: GoogleFonts.inter(color: AppTheme.textPrimary),
      ),
      content: SizedBox(
        width: 400,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Name', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
            const SizedBox(height: 8),
            TextField(
              controller: _nameController,
              decoration: InputDecoration(
                hintText: 'parameter_name',
                filled: true,
                fillColor: AppTheme.surfaceColor,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              style: GoogleFonts.firaCode(color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 16),
            Text('Description', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
            const SizedBox(height: 8),
            TextField(
              controller: _descController,
              maxLines: 2,
              decoration: InputDecoration(
                hintText: 'What this parameter is for',
                filled: true,
                fillColor: AppTheme.surfaceColor,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
              ),
              style: GoogleFonts.inter(color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Type', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        decoration: BoxDecoration(
                          color: AppTheme.surfaceColor,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: AppTheme.borderColor),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _type,
                            isExpanded: true,
                            dropdownColor: AppTheme.cardColor,
                            items: ['string', 'number', 'integer', 'boolean', 'array', 'object']
                                .map((t) => DropdownMenuItem(
                                      value: t,
                                      child: Text(t, style: GoogleFonts.firaCode(color: AppTheme.textPrimary)),
                                    ))
                                .toList(),
                            onChanged: (v) => setState(() => _type = v!),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Required', style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
                    const SizedBox(height: 8),
                    Switch(
                      value: _required,
                      onChanged: (v) => setState(() => _required = v),
                      activeColor: AppTheme.primaryColor,
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
          child: Text('Cancel', style: GoogleFonts.inter(color: AppTheme.textSecondary)),
        ),
        ElevatedButton(
          onPressed: () {
            if (_nameController.text.isNotEmpty) {
              widget.onSave(ToolParameter(
                name: _nameController.text,
                description: _descController.text,
                type: _type,
                required: _required,
              ));
              Navigator.of(context).pop();
            }
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}
