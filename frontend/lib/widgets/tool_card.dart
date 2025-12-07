import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models/tool.dart';
import '../theme/app_theme.dart';

class ToolCard extends StatefulWidget {
  final Tool tool;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback? onDelete;

  const ToolCard({
    super.key,
    required this.tool,
    this.isSelected = false,
    required this.onTap,
    this.onDelete,
  });

  @override
  State<ToolCard> createState() => _ToolCardState();
}

class _ToolCardState extends State<ToolCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: widget.isSelected 
                ? AppTheme.primaryColor.withOpacity(0.04)
                : _isHovered 
                    ? AppTheme.cardHoverColor 
                    : AppTheme.cardColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: widget.isSelected 
                  ? AppTheme.primaryColor.withOpacity(0.2)
                  : _isHovered 
                      ? AppTheme.borderColor 
                      : Colors.transparent, // Cleaner look in light mode
            ),
            boxShadow: _isHovered || widget.isSelected
                ? [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.04),
                      blurRadius: 8,
                      offset: const Offset(0, 4),
                    )
                  ]
                : [],
          ),
          child: Row(
            children: [
              // Type icon
              _buildTypeIcon(),
              const SizedBox(width: 16),
              
              // Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          widget.tool.name,
                          style: GoogleFonts.inter(
                            color: AppTheme.textPrimary,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 8),
                        _buildStatusBadge(),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.tool.description,
                      style: GoogleFonts.inter(
                        color: AppTheme.textSecondary,
                        fontSize: 13,
                        height: 1.4,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (widget.tool.url != null) ...[
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.successColor.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              widget.tool.method ?? 'GET',
                              style: GoogleFonts.firaCode(
                                color: AppTheme.successColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              widget.tool.url!,
                              style: GoogleFonts.firaCode(
                                color: AppTheme.textTertiary,
                                fontSize: 11,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              
              // Meta info
              if (_isHovered || widget.isSelected) ...[
                const SizedBox(width: 16),
                _buildActions(),
              ] else ...[
                const SizedBox(width: 16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'v${widget.tool.version}',
                      style: GoogleFonts.firaCode(
                        color: AppTheme.textTertiary,
                        fontSize: 11,
                      ),
                    ),
                    if (widget.tool.createdBy != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        widget.tool.createdBy!.split('@').first,
                        style: GoogleFonts.inter(
                          color: AppTheme.textTertiary,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ],
          ),
        ),
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
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(icon, color: color, size: 22),
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
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
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

  Widget _buildActions() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _ActionButton(
          icon: Icons.play_arrow,
          tooltip: 'Run',
          onTap: widget.onTap,
        ),
        const SizedBox(width: 4),
        _ActionButton(
          icon: Icons.edit_outlined,
          tooltip: 'Edit',
          onTap: widget.onTap,
        ),
        const SizedBox(width: 4),
        _ActionButton(
          icon: Icons.delete_outline,
          tooltip: 'Delete',
          color: AppTheme.errorColor,
          onDelete: widget.onDelete, // Changed to specific param
        ),
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final Color? color;
  final VoidCallback? onTap;
  final VoidCallback? onDelete; // Added to distinguish delete action

  const _ActionButton({
    required this.icon,
    required this.tooltip,
    this.color,
    this.onTap,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onDelete ?? onTap,
          borderRadius: BorderRadius.circular(6),
          child: Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(6),
              color: color != null ? color!.withOpacity(0.05) : null,
            ),
            child: Icon(
              icon,
              size: 18,
              color: color ?? AppTheme.textSecondary,
            ),
          ),
        ),
      ),
    );
  }
}
