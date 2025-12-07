import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../models/tool.dart';
import '../providers/tools_provider.dart';
import '../theme/app_theme.dart';

class ToolDetailPanel extends StatefulWidget {
  final Tool tool;
  final VoidCallback onClose;

  const ToolDetailPanel({
    super.key,
    required this.tool,
    required this.onClose,
  });

  @override
  State<ToolDetailPanel> createState() => _ToolDetailPanelState();
}

class _ToolDetailPanelState extends State<ToolDetailPanel> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final Map<String, TextEditingController> _paramControllers = {};
  bool _isExecuting = false;
  Map<String, dynamic>? _executionResult;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _initParamControllers();
  }

  void _initParamControllers() {
    _paramControllers.clear();
    for (final param in widget.tool.parameters) {
      _paramControllers[param.name] = TextEditingController(
        text: param.defaultValue?.toString() ?? '',
      );
    }
  }

  @override
  void didUpdateWidget(ToolDetailPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.tool.id != widget.tool.id) {
      _initParamControllers();
      _executionResult = null;
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    for (final controller in _paramControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.sidebarColor,
        border: Border(
          left: BorderSide(color: AppTheme.borderColor),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(),
          _buildToolInfo(),
          _buildTabs(),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildTestTab(),
                _buildDetailsTab(),
                _buildCodeTab(),
              ],
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
        color: AppTheme.surfaceColor, // Distinct header background
      ),
      child: Row(
        children: [
          _buildTypeIcon(),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        widget.tool.name,
                        style: GoogleFonts.inter(
                          color: AppTheme.textPrimary,
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    _buildStatusBadge(),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${widget.tool.typeLabel} • v${widget.tool.version}',
                  style: GoogleFonts.inter(
                    color: AppTheme.textTertiary,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: widget.onClose,
            icon: const Icon(Icons.close),
            color: AppTheme.textTertiary,
            iconSize: 20,
          ),
        ],
      ),
    );
  }

  Widget _buildTypeIcon() {
    IconData icon;
    Color color;
    
    switch (widget.tool.type) {
      case ToolType.function:
        icon = Icons.code;
        color = const Color(0xFF0891B2); // Cyan-600
        break;
      case ToolType.http:
        icon = Icons.http;
        color = const Color(0xFF7C3AED); // Violet-600
        break;
      case ToolType.db:
        icon = Icons.storage;
        color = const Color(0xFFD97706); // Amber-600
        break;
    }

    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Icon(icon, color: color, size: 24),
    );
  }

  Widget _buildStatusBadge() {
    Color color;
    String label;
    
    switch (widget.tool.status) {
      case ToolStatus.draft:
        color = AppTheme.textTertiary;
        label = 'Draft';
        break;
      case ToolStatus.pendingReview:
        color = AppTheme.warningColor;
        label = 'Pending';
        break;
      case ToolStatus.approved:
        color = AppTheme.successColor;
        label = 'Approved';
        break;
      case ToolStatus.rejected:
        color = AppTheme.errorColor;
        label = 'Rejected';
        break;
      case ToolStatus.published:
        color = AppTheme.infoColor;
        label = 'Published';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildToolInfo() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.borderColor)),
        color: AppTheme.surfaceColor,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.tool.description,
            style: GoogleFonts.inter(
              color: AppTheme.textSecondary,
              fontSize: 14,
              height: 1.5,
            ),
          ),
          if (widget.tool.url != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.successColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      widget.tool.method ?? 'GET',
                      style: GoogleFonts.firaCode(
                        color: AppTheme.successColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      widget.tool.url!,
                      style: GoogleFonts.firaCode(
                        color: AppTheme.textSecondary,
                        fontSize: 12,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: widget.tool.url!));
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('URL copied to clipboard')),
                      );
                    },
                    icon: const Icon(Icons.copy, size: 16),
                    color: AppTheme.textTertiary,
                    constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTabs() {
    return Container(
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.borderColor)),
        color: AppTheme.surfaceColor,
      ),
      child: TabBar(
        controller: _tabController,
        labelColor: AppTheme.primaryColor,
        unselectedLabelColor: AppTheme.textTertiary,
        indicatorColor: AppTheme.primaryColor,
        indicatorSize: TabBarIndicatorSize.label,
        indicatorWeight: 2,
        labelStyle: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w500),
        tabs: const [
          Tab(text: 'Test'),
          Tab(text: 'Details'),
          Tab(text: 'Code'),
        ],
      ),
    );
  }

  Widget _buildTestTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Parameters',
            style: GoogleFonts.inter(
              color: AppTheme.textPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          
          if (widget.tool.parameters.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surfaceColor,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: AppTheme.textTertiary, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    'This tool has no parameters',
                    style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
                  ),
                ],
              ),
            )
          else
            ...widget.tool.parameters.map((param) => _buildParamField(param)),
          
          const SizedBox(height: 24),
          
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _isExecuting ? null : _executeTool,
              icon: _isExecuting 
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.play_arrow, size: 20),
              label: Text(_isExecuting ? 'Running...' : 'Run Tool'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.accentColor,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
          
          if (_executionResult != null) ...[
            const SizedBox(height: 24),
            _buildExecutionResult(),
          ],
        ],
      ),
    );
  }

  Widget _buildParamField(ToolParameter param) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                param.name,
                style: GoogleFonts.firaCode(
                  color: AppTheme.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceColor,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: AppTheme.borderColor),
                ),
                child: Text(
                  param.type,
                  style: GoogleFonts.firaCode(
                    color: AppTheme.textTertiary,
                    fontSize: 10,
                  ),
                ),
              ),
              if (param.required) ...[
                const SizedBox(width: 6),
                Text('*', style: GoogleFonts.inter(color: AppTheme.errorColor, fontSize: 14)),
              ],
            ],
          ),
          const SizedBox(height: 4),
          Text(
            param.description,
            style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 12),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _paramControllers[param.name],
            decoration: InputDecoration(
              hintText: 'Enter ${param.name}...',
              filled: true,
              fillColor: AppTheme.surfaceColor,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
                borderSide: const BorderSide(color: AppTheme.borderColor),
              ),
              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            ),
            style: GoogleFonts.firaCode(color: AppTheme.textPrimary, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Widget _buildExecutionResult() {
    final success = _executionResult!['success'] as bool? ?? false;
    final executionTime = _executionResult!['execution_time_ms'];
    
    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: success ? AppTheme.successColor.withOpacity(0.3) : AppTheme.errorColor.withOpacity(0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: success 
                  ? AppTheme.successColor.withOpacity(0.1) 
                  : AppTheme.errorColor.withOpacity(0.1),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(7)),
            ),
            child: Row(
              children: [
                Icon(
                  success ? Icons.check_circle : Icons.error,
                  color: success ? AppTheme.successColor : AppTheme.errorColor,
                  size: 16,
                ),
                const SizedBox(width: 8),
                Text(
                  success ? 'Success' : 'Error',
                  style: GoogleFonts.inter(
                    color: success ? AppTheme.successColor : AppTheme.errorColor,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const Spacer(),
                if (executionTime != null)
                  Text(
                    '${executionTime}ms',
                    style: GoogleFonts.firaCode(color: AppTheme.textTertiary, fontSize: 11),
                  ),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            child: SelectableText(
              const JsonEncoder.withIndent('  ').convert(_executionResult),
              style: GoogleFonts.firaCode(
                color: AppTheme.textSecondary,
                fontSize: 12,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailsTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildDetailSection('General', [
            _DetailItem('ID', widget.tool.id),
            _DetailItem('Type', widget.tool.typeLabel),
            _DetailItem('Status', widget.tool.statusLabel),
            _DetailItem('Version', widget.tool.version),
            if (widget.tool.createdBy != null)
              _DetailItem('Owner', widget.tool.createdBy!),
          ]),
          
          const SizedBox(height: 24),
          
          _buildDetailSection('Execution', [
            _DetailItem('Timeout', '${widget.tool.timeoutSeconds}s'),
            _DetailItem('Return Type', widget.tool.returnType.name.toUpperCase()),
            _DetailItem('Return Target', widget.tool.returnTarget.name.toUpperCase()),
          ]),
          
          if (widget.tool.parameters.isNotEmpty) ...[
            const SizedBox(height: 24),
            Text(
              'Parameters (${widget.tool.parameters.length})',
              style: GoogleFonts.inter(
                color: AppTheme.textPrimary,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            ...widget.tool.parameters.map((param) => _buildParamDetail(param)),
          ],
        ],
      ),
    );
  }

  Widget _buildDetailSection(String title, List<_DetailItem> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: GoogleFonts.inter(
            color: AppTheme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppTheme.surfaceColor,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppTheme.borderColor),
          ),
          child: Column(
            children: items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 100,
                    child: Text(
                      item.label,
                      style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 13),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      item.value,
                      style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 13),
                    ),
                  ),
                ],
              ),
            )).toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildParamDetail(ToolParameter param) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderColor),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: AppTheme.primaryColor.withOpacity(0.05),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              param.type,
              style: GoogleFonts.firaCode(
                color: AppTheme.primaryColor,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      param.name,
                      style: GoogleFonts.firaCode(
                        color: AppTheme.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    if (param.required) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                          color: AppTheme.errorColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'required',
                          style: GoogleFonts.inter(
                            color: AppTheme.errorColor,
                            fontSize: 9,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  param.description,
                  style: GoogleFonts.inter(color: AppTheme.textTertiary, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCodeTab() {
    String code = widget.tool.functionCode ?? _generateExampleCode();
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Row(
            children: [
              Text(
                widget.tool.type == ToolType.function ? 'Source Code' : 'Usage Example',
                style: GoogleFonts.inter(
                  color: AppTheme.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: code));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Code copied to clipboard')),
                  );
                },
                icon: const Icon(Icons.copy, size: 16),
                label: const Text('Copy'),
                style: TextButton.styleFrom(foregroundColor: AppTheme.textSecondary),
              ),
            ],
          ),
        ),
        Expanded(
          child: Container(
            margin: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E1E), // Keep dark editor background
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.borderColor),
            ),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: SelectableText(
                code,
                style: GoogleFonts.firaCode(
                  color: const Color(0xFFD4D4D4), // Keep light text for dark editor
                  fontSize: 12,
                  height: 1.6,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  String _generateExampleCode() {
    if (widget.tool.type == ToolType.http) {
      return '''
import requests

def call_${_toSnakeCase(widget.tool.name)}(${widget.tool.parameters.map((p) => p.name).join(', ')}):
    """${widget.tool.description}"""
    
    url = "${widget.tool.url}"
    
    payload = {
${widget.tool.parameters.map((p) => '        "${p.name}": ${p.name},').join('\n')}
    }
    
    headers = {
        "Content-Type": "application/json",
${widget.tool.headers?.entries.map((e) => '        "${e.key}": "${e.value}",').join('\n') ?? ''}
    }
    
    response = requests.${(widget.tool.method ?? 'get').toLowerCase()}(
        url, 
        json=payload, 
        headers=headers,
        timeout=${widget.tool.timeoutSeconds}
    )
    
    return response.json()
''';
    } else if (widget.tool.type == ToolType.db) {
      return '''
import psycopg2

def execute_${_toSnakeCase(widget.tool.name)}(query, params=None):
    """${widget.tool.description}"""
    
    conn = psycopg2.connect(
        host="${widget.tool.host ?? 'localhost'}",
        port=${widget.tool.port ?? 5432},
        database="${widget.tool.database ?? 'mydb'}",
        user="\${DB_USER}",
        password="\${DB_PASSWORD}"
    )
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        return results
    finally:
        cursor.close()
        conn.close()
''';
    }
    
    return '# No code available';
  }

  String _toSnakeCase(String text) {
    return text
        .replaceAllMapped(RegExp(r'[A-Z]'), (m) => '_${m.group(0)!.toLowerCase()}')
        .replaceAll(RegExp(r'[^a-z0-9_]'), '_')
        .replaceAll(RegExp(r'_+'), '_')
        .replaceFirst(RegExp(r'^_'), '');
  }

  Future<void> _executeTool() async {
    setState(() {
      _isExecuting = true;
      _executionResult = null;
    });

    final params = <String, dynamic>{};
    for (final param in widget.tool.parameters) {
      params[param.name] = _paramControllers[param.name]?.text ?? '';
    }

    final provider = context.read<ToolsProvider>();
    final result = await provider.executeTool(widget.tool, params);

    setState(() {
      _isExecuting = false;
      _executionResult = result;
    });
  }
}

class _DetailItem {
  final String label;
  final String value;
  
  _DetailItem(this.label, this.value);
}
