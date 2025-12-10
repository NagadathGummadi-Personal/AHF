import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/theme/app_theme.dart';
import '../models/tool_model.dart';

/// Detail panel for viewing tool information.
class ToolDetailPanel extends StatelessWidget {
  final Tool tool;
  final VoidCallback onClose;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const ToolDetailPanel({
    super.key,
    required this.tool,
    required this.onClose,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final typeColor = AppTheme.getToolTypeColor(tool.toolType);
    final typeIcon = AppTheme.getToolTypeIcon(tool.toolType);
    final border = theme.dividerColor;
    
    return Container(
      color: theme.colorScheme.surface,
      child: Column(
        children: [
          // Header
          _buildHeader(typeColor, typeIcon, theme),
          // Tabbed content placeholder (future enhancement); currently single scroll
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSection(
                    title: 'Description',
                    child: Text(tool.description, style: theme.textTheme.bodyMedium),
                  ),
                  const SizedBox(height: 24),
                  if (tool.parameters.isNotEmpty) ...[
                    _buildSection(
                      title: 'Parameters',
                      child: _buildParameters(theme, border),
                    ),
                    const SizedBox(height: 24),
                  ],
                  _buildTypeConfig(typeColor),
                  const SizedBox(height: 24),
                  _buildSection(
                    title: 'Execution Settings',
                    child: _buildExecutionSettings(),
                  ),
                  if (tool.retry != null && tool.retry!['enabled'] == true) ...[
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Retry Configuration',
                      child: _buildKeyValueList(tool.retry!),
                    ),
                  ],
                  if (tool.idempotency != null && tool.idempotency!['enabled'] == true) ...[
                    const SizedBox(height: 24),
                    _buildSection(
                      title: 'Idempotency',
                      child: _buildKeyValueList(tool.idempotency!),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(Color typeColor, IconData typeIcon, ThemeData theme) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: theme.dividerColor)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: typeColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(typeIcon, color: typeColor, size: 24),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(tool.toolName, style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: typeColor.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            tool.toolTypeLabel,
                            style: GoogleFonts.inter(
                              color: typeColor,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                          Text('v${tool.version}', style: theme.textTheme.labelMedium),
                      ],
                    ),
                  ],
                ),
              ),
              IconButton(
                onPressed: onClose,
                icon: const Icon(Icons.close, size: 20),
                color: theme.iconTheme.color,
                tooltip: 'Close',
              ),
            ],
          ),
          const SizedBox(height: 16),
          
          // ID with copy button
          Row(
            children: [
              Text('ID: ', style: theme.textTheme.labelMedium),
              Text(
                tool.id,
                style: GoogleFonts.firaCode(
                  fontSize: 13,
                  color: theme.textTheme.bodySmall?.color,
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: () => _copyToClipboard(tool.id),
                icon: const Icon(Icons.copy, size: 16),
                iconSize: 16,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                color: AppTheme.textTertiaryDark,
                tooltip: 'Copy ID',
              ),
            ],
          ),
          
          const SizedBox(height: 16),
          
          // Action buttons
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: onEdit,
                icon: const Icon(Icons.edit_outlined, size: 18),
                label: const Text('Edit'),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: onDelete,
                icon: const Icon(Icons.delete_outline, size: 18),
                label: const Text('Delete'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.error,
                  side: const BorderSide(color: AppTheme.error),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSection({required String title, required Widget child}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
          Text(title, style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600, color: AppTheme.textSecondaryDark)),
        const SizedBox(height: 12),
        child,
      ],
    );
  }

  Widget _buildParameters(ThemeData theme, Color border) {
    final bg = theme.colorScheme.surface;
    return Column(
      children: tool.parameters.map((param) {
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: border),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Name and type
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          param.name,
                          style: GoogleFonts.firaCode(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: theme.textTheme.bodyLarge?.color,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: AppTheme.primary.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            param.type,
                            style: GoogleFonts.firaCode(
                              fontSize: 11,
                              color: AppTheme.primary,
                            ),
                          ),
                        ),
                        if (param.required) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: AppTheme.error.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'required',
                              style: GoogleFonts.inter(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.error,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    if (param.description.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(param.description, style: theme.textTheme.bodyMedium),
                    ],
                  ],
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildTypeConfig(Color typeColor) {
    switch (tool.toolType) {
      case 'http':
        return _buildSection(
          title: 'HTTP Configuration',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildConfigRow('Method', tool.method ?? 'GET'),
              _buildConfigRow('URL', tool.url ?? ''),
              if (tool.headers != null && tool.headers!.isNotEmpty)
                _buildConfigRow(
                  'Headers',
                  tool.headers!.entries.map((e) => '${e.key}: ${e.value}').join('\n'),
                ),
            ],
          ),
        );
      
      case 'function':
        return _buildSection(
          title: 'Function Code',
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E1E),
              borderRadius: BorderRadius.circular(8),
            ),
            child: SelectableText(
              tool.functionCode ?? '# No code defined',
              style: GoogleFonts.firaCode(
                fontSize: 12,
                color: const Color(0xFFD4D4D4),
                height: 1.5,
              ),
            ),
          ),
        );
      
      case 'db':
        return _buildSection(
          title: 'Database Configuration',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildConfigRow('Driver', tool.driver ?? 'postgresql'),
              _buildConfigRow('Host', tool.host ?? 'localhost'),
              _buildConfigRow('Port', tool.port?.toString() ?? '5432'),
              _buildConfigRow('Database', tool.database ?? ''),
            ],
          ),
        );
      
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildExecutionSettings() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildConfigRow('Timeout', '${tool.timeoutS} seconds'),
        _buildConfigRow('Return Type', tool.returnType.toUpperCase()),
        _buildConfigRow('Return Target', _formatReturnTarget(tool.returnTarget)),
      ],
    );
  }

  Widget _buildConfigRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w500, color: AppTheme.textSecondaryDark),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: GoogleFonts.inter(fontSize: 13, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildKeyValueList(Map<String, dynamic> data) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: data.entries.map((entry) {
        return _buildConfigRow(
          _formatKey(entry.key),
          entry.value?.toString() ?? 'null',
        );
      }).toList(),
    );
  }

  String _formatKey(String key) {
    return key
        .replaceAll('_', ' ')
        .split(' ')
        .map((word) => word.isEmpty ? '' : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  String _formatReturnTarget(String target) {
    switch (target) {
      case 'llm':
        return 'LLM (continue conversation)';
      case 'human':
        return 'Human (direct to user)';
      case 'agent':
        return 'Agent (for agent processing)';
      case 'step':
        return 'Step (workflow step output)';
      default:
        return target;
    }
  }

  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
  }
}

