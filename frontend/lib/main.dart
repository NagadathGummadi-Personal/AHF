import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'providers/tools_provider.dart';
import 'screens/tools_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const AHFApp());
}

class AHFApp extends StatelessWidget {
  const AHFApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ToolsProvider()),
      ],
      child: MaterialApp(
        title: 'AHF',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.theme,
        home: const MainLayout(),
      ),
    );
  }
}

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _selectedIndex = 1; // Default to Tools for this task
  bool _isSidebarCollapsed = false; // Keep open by default for clarity

  final List<NavItem> _navItems = [
    NavItem(id: 'agents', icon: Icons.smart_toy_outlined, label: 'Agents'),
    NavItem(id: 'tools', icon: Icons.build_circle_outlined, label: 'Tools'),
    NavItem(id: 'workflows', icon: Icons.account_tree_outlined, label: 'Workflows'),
    NavItem(id: 'knowledge', icon: Icons.library_books_outlined, label: 'Knowledge'),
    NavItem(id: 'settings', icon: Icons.settings_outlined, label: 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.backgroundColor,
      body: Row(
        children: [
          // Minimal Sidebar
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: _isSidebarCollapsed ? 72 : 220,
            decoration: const BoxDecoration(
              color: AppTheme.sidebarColor,
              border: Border(right: BorderSide(color: AppTheme.borderColor)),
            ),
            child: Column(
              children: [
                _buildLogo(),
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    itemCount: _navItems.length,
                    itemBuilder: (context, index) => _buildNavItem(_navItems[index], index),
                  ),
                ),
                _buildCollapseButton(),
              ],
            ),
          ),
          
          // Main Content
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return Container(
      height: 64,
      padding: EdgeInsets.symmetric(horizontal: _isSidebarCollapsed ? 0 : 16),
      alignment: _isSidebarCollapsed ? Alignment.center : Alignment.centerLeft,
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppTheme.borderColor)),
      ),
      child: _isSidebarCollapsed 
          ? const Icon(Icons.hub, color: AppTheme.primaryColor)
          : Text(
              'AHF',
              style: GoogleFonts.inter(
                color: AppTheme.textPrimary,
                fontSize: 20,
                fontWeight: FontWeight.w700,
              ),
            ),
    );
  }

  Widget _buildNavItem(NavItem item, int index) {
    final isSelected = _selectedIndex == index;
    return Tooltip(
      message: _isSidebarCollapsed ? item.label : '',
      waitDuration: const Duration(milliseconds: 500),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () => setState(() => _selectedIndex = index),
          child: Container(
            height: 48,
            margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: isSelected ? Colors.white : Colors.transparent,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: isSelected ? AppTheme.borderColor : Colors.transparent),
              boxShadow: isSelected
                  ? [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.03),
                        blurRadius: 6,
                        offset: const Offset(0, 3),
                      )
                    ]
                  : null,
            ),
            child: Row(
              mainAxisAlignment: _isSidebarCollapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
              children: [
                Container(
                  width: 4,
                  height: 24,
                  margin: const EdgeInsets.only(left: 6, right: 10),
                  decoration: BoxDecoration(
                    color: isSelected ? AppTheme.primaryColor : Colors.transparent,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                Icon(
                  item.icon,
                  size: 20,
                  color: isSelected ? AppTheme.primaryColor : AppTheme.textSecondary,
                ),
                if (!_isSidebarCollapsed) ...[
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      item.label,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: isSelected ? AppTheme.textPrimary : AppTheme.textSecondary,
                        fontSize: 13,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCollapseButton() {
    return Container(
      padding: const EdgeInsets.all(12),
      child: IconButton(
        onPressed: () => setState(() => _isSidebarCollapsed = !_isSidebarCollapsed),
        icon: Icon(
          _isSidebarCollapsed ? Icons.chevron_right : Icons.chevron_left,
          color: AppTheme.textTertiary,
          size: 20,
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_selectedIndex == 1) { // Tools
      return const ToolsScreen();
    }
    
    return Center(
      child: Text(
        '${_navItems[_selectedIndex].label} Module\nComing Soon',
        textAlign: TextAlign.center,
        style: GoogleFonts.inter(
          color: AppTheme.textTertiary,
          fontSize: 16,
        ),
      ),
    );
  }
}

class NavItem {
  final String id;
  final IconData icon;
  final String label;

  NavItem({required this.id, required this.icon, required this.label});
}
