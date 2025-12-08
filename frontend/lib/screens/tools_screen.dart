import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../models/tool.dart';
import '../providers/tools_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/tool_card.dart';
import '../widgets/tool_detail_panel.dart';
import '../widgets/create_tool_dialog.dart';

class ToolsScreen extends StatefulWidget {
  const ToolsScreen({super.key});

  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<ToolsProvider>();
      if (provider.tools.isEmpty && !provider.isLoading) {
        provider.fetchTools();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<ToolsProvider>(
      builder: (context, provider, child) {
        return Row(
          children: [
            // Main Content Area
            Expanded(
              flex: provider.selectedTool != null ? 3 : 1,
              child: Container(
                color: AppTheme.backgroundColor,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildHeader(context, provider),
                    Expanded(
                      child: _buildContent(provider),
                    ),
                  ],
                ),
              ),
            ),
            
            // Detail Panel (when tool is selected)
            if (provider.selectedTool != null)
              Expanded(
                flex: 2,
                child: ToolDetailPanel(
                  tool: provider.selectedTool!,
                  onClose: () => provider.selectTool(null),
                  onEdit: () => _showCreateToolPanel(context, provider.selectedTool),
                ),
              ),
          ],
        );
      },
    );
  }

  Widget _buildHeader(BuildContext context, ToolsProvider provider) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.borderColor)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Tools',
                    style: GoogleFonts.inter(
                      color: AppTheme.textPrimary,
                      fontSize: 24,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Manage and monitor your AI tools',
                    style: GoogleFonts.inter(
                      color: AppTheme.textSecondary,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              // Actions
              OutlinedButton.icon(
                onPressed: () => provider.fetchTools(),
                icon: Icon(
                  provider.isLoading ? Icons.hourglass_empty : Icons.refresh,
                  size: 16,
                ),
                label: const Text('Refresh'),
                style: OutlinedButton.styleFrom(
                  backgroundColor: Colors.white,
                  foregroundColor: AppTheme.textSecondary,
                  side: const BorderSide(color: AppTheme.borderColor),
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
              ),
              const SizedBox(width: 12),
              ElevatedButton.icon(
                onPressed: () => _showCreateToolPanel(context),
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Create Tool'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryColor,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  elevation: 0,
                  shadowColor: Colors.transparent,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          _buildSearchAndFilters(context, provider),
        ],
      ),
    );
  }

  Widget _buildSearchAndFilters(BuildContext context, ToolsProvider provider) {
    return Row(
      children: [
        // Search
        Expanded(
          flex: 2,
          child: Container(
            height: 40,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.borderColor),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.02),
                  blurRadius: 2,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: TextField(
              controller: _searchController,
              onChanged: provider.setSearchQuery,
              decoration: InputDecoration(
                hintText: 'Search tools...',
                prefixIcon: const Icon(Icons.search, color: AppTheme.textTertiary, size: 18),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 16),
                        onPressed: () {
                          _searchController.clear();
                          provider.setSearchQuery('');
                        },
                        color: AppTheme.textTertiary,
                      )
                    : null,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 8), // Adjusted padding
                isDense: true,
              ),
              style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 14),
              textAlignVertical: TextAlignVertical.center, // Center text vertically
            ),
          ),
        ),
        const SizedBox(width: 12),
        
        // Type Filter
        _FilterDropdown(
          value: provider.filterType,
          hint: 'All Types',
          items: [
            _FilterItem(null, 'All Types', Icons.apps),
            _FilterItem(ToolType.function, 'Function', Icons.code),
            _FilterItem(ToolType.http, 'HTTP', Icons.http),
            _FilterItem(ToolType.db, 'Database', Icons.storage),
          ],
          onChanged: provider.setFilterType,
        ),
        
        const Spacer(),
        
        // Tool count
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.sidebarColor,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: AppTheme.borderColor),
          ),
          child: Text(
            '${provider.tools.length} results',
            style: GoogleFonts.inter(
              color: AppTheme.textSecondary,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildContent(ToolsProvider provider) {
    if (provider.isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaryColor),
      );
    }

    if (provider.error != null) {
      return _buildErrorState(provider);
    }

    if (provider.tools.isEmpty) {
      return _buildEmptyState();
    }

    return _buildToolsList(provider);
  }

  Widget _buildErrorState(ToolsProvider provider) {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(32),
        constraints: const BoxConstraints(maxWidth: 400),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: AppTheme.errorColor.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.cloud_off,
                size: 24,
                color: AppTheme.errorColor,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Connection Error',
              style: GoogleFonts.inter(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              provider.error!,
              style: GoogleFonts.inter(
                color: AppTheme.textSecondary,
                fontSize: 14,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton.icon(
                  onPressed: () => provider.fetchTools(),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Retry'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Container(
        padding: const EdgeInsets.all(32),
        constraints: const BoxConstraints(maxWidth: 400),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: AppTheme.sidebarColor,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.borderColor),
              ),
              child: const Icon(
                Icons.build_outlined,
                size: 32,
                color: AppTheme.textTertiary,
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'No tools yet',
              style: GoogleFonts.inter(
                color: AppTheme.textPrimary,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Create your first tool to extend your AI agents with custom capabilities.',
              style: GoogleFonts.inter(
                color: AppTheme.textSecondary,
                fontSize: 14,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.center,
              children: [
                _QuickCreateButton(
                  icon: Icons.code,
                  label: 'Function',
                  color: const Color(0xFF0891B2),
                  onTap: () => _showCreateToolDialog(context, ToolType.function),
                ),
                _QuickCreateButton(
                  icon: Icons.http,
                  label: 'HTTP',
                  color: const Color(0xFF7C3AED),
                  onTap: () => _showCreateToolDialog(context, ToolType.http),
                ),
                _QuickCreateButton(
                  icon: Icons.storage,
                  label: 'Database',
                  color: const Color(0xFFD97706),
                  onTap: () => _showCreateToolDialog(context, ToolType.db),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToolsList(ToolsProvider provider) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      itemCount: provider.tools.length,
      itemBuilder: (context, index) {
        final tool = provider.tools[index];
        return ToolCard(
          tool: tool,
          isSelected: provider.selectedTool?.id == tool.id,
          onTap: () => provider.selectTool(tool),
          onDelete: () => _deleteTool(context, provider, tool),
        );
      },
    );
  }

  void _showCreateToolDialog(BuildContext context, [ToolType? type]) {
    _showCreateToolPanel(context, null, type);
  }

  void _showCreateToolPanel(BuildContext context, [Tool? editTool, ToolType? type]) {
    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Create Tool',
      transitionDuration: const Duration(milliseconds: 200),
      pageBuilder: (ctx, anim1, anim2) {
        return Align(
          alignment: Alignment.centerRight,
          child: Material(
            color: Colors.transparent,
            child: Container(
              width: MediaQuery.of(context).size.width * 0.5,
              height: MediaQuery.of(context).size.height,
              decoration: BoxDecoration(
                color: Colors.white,
                border: const Border(left: BorderSide(color: AppTheme.borderColor)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.08),
                    blurRadius: 16,
                    offset: const Offset(-4, 0),
                  ),
                ],
              ),
              child: CreateToolDialog(initialType: type ?? editTool?.type, editTool: editTool),
            ),
          ),
        );
      },
      transitionBuilder: (ctx, anim, _, child) {
        final offset = Tween<Offset>(begin: const Offset(0.2, 0), end: Offset.zero)
            .animate(CurvedAnimation(parent: anim, curve: Curves.easeOut));
        return SlideTransition(
          position: offset,
          child: child,
        );
      },
    );
  }

  Future<void> _deleteTool(BuildContext context, ToolsProvider provider, Tool tool) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Colors.white,
        title: Text('Delete Tool', style: GoogleFonts.inter(color: AppTheme.textPrimary, fontWeight: FontWeight.w600)),
        content: Text(
          'Are you sure you want to delete "${tool.name}"? This action cannot be undone.',
          style: GoogleFonts.inter(color: AppTheme.textSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text('Cancel', style: GoogleFonts.inter(color: AppTheme.textSecondary)),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.errorColor,
              foregroundColor: Colors.white,
            ),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final result = await provider.deleteTool(tool.id);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message']),
            backgroundColor: result['success'] ? AppTheme.successColor : AppTheme.errorColor,
          ),
        );
      }
    }
  }
}

class _FilterDropdown extends StatelessWidget {
  final ToolType? value;
  final String hint;
  final List<_FilterItem> items;
  final Function(ToolType?) onChanged;

  const _FilterDropdown({
    required this.value,
    required this.hint,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppTheme.borderColor),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 2,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<ToolType?>(
          value: value,
          hint: Text(hint, style: GoogleFonts.inter(color: AppTheme.textSecondary, fontSize: 13)),
          dropdownColor: Colors.white,
          icon: const Icon(Icons.keyboard_arrow_down, color: AppTheme.textTertiary, size: 18),
          elevation: 2,
          style: GoogleFonts.inter(color: AppTheme.textPrimary, fontSize: 13),
          items: items.map((item) => DropdownMenuItem(
            value: item.value,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(item.icon, size: 16, color: AppTheme.textSecondary),
                const SizedBox(width: 8),
                Text(item.label),
              ],
            ),
          )).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }
}

class _FilterItem {
  final ToolType? value;
  final String label;
  final IconData icon;

  _FilterItem(this.value, this.label, this.icon);
}

class _QuickCreateButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _QuickCreateButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          decoration: BoxDecoration(
            color: color.withOpacity(0.05),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withOpacity(0.2)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 10),
              Text(
                label,
                style: GoogleFonts.inter(
                  color: color,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
