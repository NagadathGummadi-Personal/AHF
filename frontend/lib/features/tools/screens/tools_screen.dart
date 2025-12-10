import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../../core/theme/app_theme.dart';
import '../models/tool_model.dart';
import '../providers/tools_provider.dart';
import '../widgets/tool_card.dart';
import '../widgets/tool_detail_panel.dart';
import '../widgets/tool_form_dialog.dart';

/// Main screen for tools management.
class ToolsScreen extends StatefulWidget {
  const ToolsScreen({super.key});

  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
  final _searchController = TextEditingController();
  bool _useTableView = false;
  bool _showFilters = true;
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ToolsProvider>().loadTools();
    });
  }
  
  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Consumer<ToolsProvider>(
      builder: (context, provider, _) {
        return Row(
          children: [
            Expanded(
              child: Column(
                children: [
                  _buildHeader(provider, isDark),
                  if (_showFilters) _buildFilters(provider, isDark),
                  Expanded(
                    child: _useTableView
                        ? _buildTable(provider, isDark)
                        : _buildToolsList(provider, isDark),
                  ),
                ],
              ),
            ),
            if (provider.selectedTool != null) ...[
              const VerticalDivider(width: 1),
              SizedBox(
                width: 520,
                child: ToolDetailPanel(
                  tool: provider.selectedTool!,
                  onClose: () => provider.selectTool(null),
                  onEdit: () => _openToolDialog(context, provider.selectedTool),
                  onDelete: () => _deleteTool(context, provider.selectedTool!),
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _buildHeader(ToolsProvider provider, bool isDark) {
    final border = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textSecondary = Theme.of(context).textTheme.bodySmall!.color ?? AppTheme.textSecondaryLight;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(bottom: BorderSide(color: border)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Tools', style: Theme.of(context).textTheme.displayMedium),
                const SizedBox(height: 4),
                Text(
                  'Manage and configure tools for your agents',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: textSecondary),
                ),
              ],
            ),
          ),
          _buildStatChip(label: 'Total', count: provider.totalCount, color: textSecondary),
          const SizedBox(width: 10),
          _buildStatChip(label: 'Function', count: provider.functionCount, color: AppTheme.functionColor),
          const SizedBox(width: 10),
          _buildStatChip(label: 'HTTP', count: provider.httpCount, color: AppTheme.httpColor),
          const SizedBox(width: 10),
          _buildStatChip(label: 'Database', count: provider.dbCount, color: AppTheme.dbColor),
          const SizedBox(width: 12),
          SegmentedButton<bool>(
            segments: const [
              ButtonSegment(value: false, label: Text('Cards'), icon: Icon(Icons.dashboard_customize_outlined)),
              ButtonSegment(value: true, label: Text('Table'), icon: Icon(Icons.table_chart_outlined)),
            ],
            selected: {_useTableView},
            onSelectionChanged: (v) => setState(() => _useTableView = v.first),
            showSelectedIcon: false,
          ),
          const SizedBox(width: 12),
          IconButton(
            tooltip: _showFilters ? 'Hide filters' : 'Show filters',
            onPressed: () => setState(() => _showFilters = !_showFilters),
            icon: Icon(_showFilters ? Icons.filter_alt_off : Icons.filter_alt),
          ),
        ],
      ),
    );
  }

  Widget _buildStatChip({
    required String label,
    required int count,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            count.toString(),
            style: GoogleFonts.inter(
              color: color,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: GoogleFonts.inter(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilters(ToolsProvider provider, bool isDark) {
    final border = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(bottom: BorderSide(color: border)),
      ),
      child: Row(
        children: [
          // Search
          Expanded(
            child: SizedBox(
              height: 44,
              child: TextField(
                controller: _searchController,
                onChanged: (value) => provider.setSearchQuery(value),
                decoration: InputDecoration(
                  hintText: 'Search tools...',
                  prefixIcon: const Icon(Icons.search, size: 18),
                  suffixIcon: provider.searchQuery.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 16),
                          onPressed: () {
                            _searchController.clear();
                            provider.setSearchQuery('');
                          },
                        )
                      : null,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          
          // Type filter
          _buildFilterChip(
            label: 'All',
            isSelected: provider.filterType == null,
            onTap: () => provider.setFilterType(null),
          ),
          const SizedBox(width: 8),
          _buildFilterChip(
            label: 'Function',
            isSelected: provider.filterType == 'function',
            color: AppTheme.functionColor,
            onTap: () => provider.setFilterType('function'),
          ),
          const SizedBox(width: 8),
          _buildFilterChip(
            label: 'HTTP',
            isSelected: provider.filterType == 'http',
            color: AppTheme.httpColor,
            onTap: () => provider.setFilterType('http'),
          ),
          const SizedBox(width: 8),
          _buildFilterChip(
            label: 'Database',
            isSelected: provider.filterType == 'db',
            color: AppTheme.dbColor,
            onTap: () => provider.setFilterType('db'),
          ),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () => _openToolDialog(context, null),
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Create Tool'),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip({
    required String label,
    required bool isSelected,
    Color? color,
    required VoidCallback onTap,
  }) {
    final effectiveColor = color ?? Theme.of(context).textTheme.bodySmall!.color ?? AppTheme.textSecondaryLight;
    
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: isSelected
                ? effectiveColor.withOpacity(0.1)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected ? effectiveColor : Theme.of(context).dividerColor,
            ),
          ),
          child: Text(
            label,
            style: GoogleFonts.inter(
              color: isSelected ? effectiveColor : AppTheme.textSecondaryDark,
              fontSize: 13,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildToolsList(ToolsProvider provider, bool isDark) {
    if (provider.isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }
    
    if (provider.tools.isEmpty) {
      return _buildEmptyState(provider);
    }
    
    return GridView.builder(
      padding: const EdgeInsets.all(20),
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 420,
        childAspectRatio: 1.55,
        crossAxisSpacing: 14,
        mainAxisSpacing: 14,
      ),
      itemCount: provider.tools.length,
      itemBuilder: (context, index) {
        final tool = provider.tools[index];
        return ToolCard(
          tool: tool,
          isSelected: provider.selectedTool?.id == tool.id,
          onTap: () => provider.selectTool(tool),
          onEdit: () => _openToolDialog(context, tool),
          isDark: isDark,
        );
      },
    );
  }

  Widget _buildTable(ToolsProvider provider, bool isDark) {
    final textStyle = Theme.of(context).textTheme.bodyMedium!;
    final border = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: border),
        ),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowHeight: 44,
            dataRowHeight: 48,
            columns: const [
              DataColumn(label: Text('Name')),
              DataColumn(label: Text('Type')),
              DataColumn(label: Text('Version')),
              DataColumn(label: Text('Params')),
              DataColumn(label: Text('Timeout')),
              DataColumn(label: Text('Updated')),
              DataColumn(label: Text('Actions')),
            ],
            rows: provider.tools.map((tool) {
              return DataRow(
                selected: provider.selectedTool?.id == tool.id,
                onSelectChanged: (_) => provider.selectTool(tool),
                cells: [
                  DataCell(Text(tool.toolName, style: textStyle)),
                  DataCell(Text(tool.toolTypeLabel, style: textStyle)),
                  DataCell(Text(tool.version, style: textStyle)),
                  DataCell(Text('${tool.parameters.length}', style: textStyle)),
                  DataCell(Text('${tool.timeoutS}s', style: textStyle)),
                  DataCell(Text(tool.updatedAt?.toIso8601String().substring(0, 10) ?? '-', style: textStyle)),
                  DataCell(Row(
                    children: [
                      IconButton(
                        tooltip: 'Edit',
                        icon: const Icon(Icons.edit_outlined, size: 18),
                        onPressed: () => _openToolDialog(context, tool),
                      ),
                      IconButton(
                        tooltip: 'Delete',
                        icon: const Icon(Icons.delete_outline, size: 18),
                        onPressed: () => _deleteTool(context, tool),
                      ),
                    ],
                  )),
                ],
              );
            }).toList(),
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(ToolsProvider provider) {
    final hasFilters = provider.searchQuery.isNotEmpty || provider.filterType != null;
    
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            hasFilters ? Icons.search_off : Icons.build_circle_outlined,
            size: 64,
            color: AppTheme.textTertiaryDark.withOpacity(0.5),
          ),
          const SizedBox(height: 16),
          Text(
            hasFilters ? 'No tools match your filters' : 'No tools yet',
            style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.textSecondaryDark),
          ),
          const SizedBox(height: 8),
          Text(
            hasFilters
                ? 'Try adjusting your search or filters'
                : 'Create your first tool to get started',
            style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w400, color: AppTheme.textTertiaryDark),
          ),
          if (!hasFilters) ...[
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _openToolDialog(context, null),
              icon: const Icon(Icons.add, size: 20),
              label: const Text('Create Tool'),
            ),
          ],
        ],
      ),
    );
  }

  void _openToolDialog(BuildContext context, Tool? tool) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(24),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: 900,
              maxHeight: MediaQuery.of(context).size.height * 0.85, // Fixed height ratio
              minHeight: 500, // Minimum height to prevent squashing
            ),
            child: ToolFormDialog(
              editTool: tool,
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _deleteTool(BuildContext context, Tool tool) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Tool'),
        content: Text('Are you sure you want to delete "${tool.toolName}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.error,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    
    if (confirmed == true && mounted) {
      final provider = context.read<ToolsProvider>();
      final result = await provider.deleteTool(tool.id);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: result['success']
                ? AppTheme.success
                : AppTheme.error,
          ),
        );
      }
    }
  }
}

