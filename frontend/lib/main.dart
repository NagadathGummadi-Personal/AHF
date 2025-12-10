import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme/app_theme.dart';
import 'core/theme/theme_controller.dart';
import 'features/tools/providers/tools_provider.dart';
import 'features/tools/screens/tools_screen.dart';

void main() {
  runApp(const AHFApp());
}

/// Root application widget.
class AHFApp extends StatelessWidget {
  const AHFApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ToolsProvider()),
        ChangeNotifierProvider(create: (_) => ThemeController()),
      ],
      child: Consumer<ThemeController>(
        builder: (context, themeCtrl, _) {
          return MaterialApp(
            title: 'AHF - AI Hub Framework',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: themeCtrl.mode,
            home: const AppShell(),
          );
        },
      ),
    );
  }
}

/// Application shell with sidebar and top bar.
class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _selectedIndex = 0;
  bool _collapsed = false;

  final List<_NavItem> _navItems = const [
    _NavItem(id: 'tools', icon: Icons.home_outlined, label: 'Tools'),
    _NavItem(id: 'agents', icon: Icons.smart_toy_outlined, label: 'Agents'),
    _NavItem(id: 'workflows', icon: Icons.account_tree_outlined, label: 'Workflows'),
    _NavItem(id: 'prompts', icon: Icons.text_snippet_outlined, label: 'Prompts'),
    _NavItem(id: 'settings', icon: Icons.settings_outlined, label: 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    final themeCtrl = context.watch<ThemeController>();
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final border = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final surface = Theme.of(context).colorScheme.surface;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: Row(
        children: [
          // Sidebar
          AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: _collapsed ? 76 : 240,
            decoration: BoxDecoration(
              color: surface,
              border: Border(right: BorderSide(color: border)),
            ),
            child: Column(
              children: [
                _SidebarHeader(collapsed: _collapsed),
                Expanded(
                  child: ListView(
                    padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
                    children: _navItems.map((item) {
                      final selected = item == _navItems[_selectedIndex];
                      return _SidebarItem(
                        item: item,
                        collapsed: _collapsed,
                        selected: selected,
                        onTap: () => setState(() => _selectedIndex = _navItems.indexOf(item)),
                      );
                    }).toList(),
                  ),
                ),
                IconButton(
                  tooltip: _collapsed ? 'Expand' : 'Collapse',
                  onPressed: () => setState(() => _collapsed = !_collapsed),
                  icon: Icon(
                    _collapsed ? Icons.chevron_right : Icons.chevron_left,
                    color: Theme.of(context).textTheme.bodySmall?.color,
                    size: 18,
                  ),
                ),
                const SizedBox(height: 12),
              ],
            ),
          ),

          // Main content + top bar
          Expanded(
            child: Column(
              children: [
                _TopBar(onToggleTheme: themeCtrl.toggle),
                Expanded(child: _buildContent()),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    switch (_navItems[_selectedIndex].id) {
      case 'tools':
        return const ToolsScreen();
      default:
        return Center(
          child: Text(
            '${_navItems[_selectedIndex].label} (coming soon)',
            style: Theme.of(context).textTheme.titleLarge,
          ),
        );
    }
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.onToggleTheme});

  final VoidCallback onToggleTheme;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final border = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final text = Theme.of(context).textTheme.titleMedium!;

    return Container(
      height: 64,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(bottom: BorderSide(color: border)),
      ),
      child: Row(
        children: [
          Text('AI Hub', style: text.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: AppTheme.primary.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppTheme.primary.withOpacity(0.35)),
            ),
            child: Row(
              children: [
                Icon(Icons.shield, size: 16, color: AppTheme.primary),
                const SizedBox(width: 6),
                Text('Prod', style: text.copyWith(color: AppTheme.primary, fontSize: 12, fontWeight: FontWeight.w700)),
              ],
            ),
          ),
          const Spacer(),
          SizedBox(
            width: 320,
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search or jump to...',
                prefixIcon: const Icon(Icons.search, size: 18),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
              ),
            ),
          ),
          const SizedBox(width: 12),
          IconButton(
            tooltip: isDark ? 'Switch to light' : 'Switch to dark',
            onPressed: onToggleTheme,
            icon: Icon(isDark ? Icons.wb_sunny_outlined : Icons.nightlight_round),
          ),
        ],
      ),
    );
  }
}

class _SidebarHeader extends StatelessWidget {
  const _SidebarHeader({required this.collapsed});
  final bool collapsed;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 64,
      padding: EdgeInsets.symmetric(horizontal: collapsed ? 0 : 16),
      alignment: collapsed ? Alignment.center : Alignment.centerLeft,
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: AppTheme.primary,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.hub, color: Colors.white, size: 20),
          ),
          if (!collapsed) ...[
            const SizedBox(width: 10),
            Text(
              'AI Hub',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
        ],
      ),
    );
  }
}

class _SidebarItem extends StatelessWidget {
  const _SidebarItem({
    required this.item,
    required this.collapsed,
    required this.selected,
    required this.onTap,
  });

  final _NavItem item;
  final bool collapsed;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final border = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textPrimary = Theme.of(context).textTheme.bodyLarge!.color!;
    final textSecondary = Theme.of(context).textTheme.bodyMedium!.color!;

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 130),
          height: 44,
          padding: EdgeInsets.symmetric(horizontal: collapsed ? 0 : 12),
          decoration: BoxDecoration(
            color: selected ? (isDark ? AppTheme.cardDark : AppTheme.cardLight) : Colors.transparent,
            borderRadius: BorderRadius.circular(10),
            border: selected ? Border.all(color: border) : null,
            boxShadow: selected
                ? [
                    BoxShadow(
                      color: AppTheme.primary.withOpacity(0.12),
                      blurRadius: 8,
                      offset: const Offset(0, 3),
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
            children: [
              Icon(item.icon, size: 20, color: selected ? AppTheme.primary : textSecondary),
              if (!collapsed) ...[
                const SizedBox(width: 10),
                Text(
                  item.label,
                  style: TextStyle(
                    color: selected ? textPrimary : textSecondary,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem {
  final String id;
  final IconData icon;
  final String label;
  const _NavItem({required this.id, required this.icon, required this.label});
}

