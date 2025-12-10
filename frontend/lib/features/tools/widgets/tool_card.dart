import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/theme/app_theme.dart';
import '../models/tool_model.dart';

/// Card widget for displaying a tool in the grid.
class ToolCard extends StatefulWidget {
  final Tool tool;
  final bool isSelected;
  final bool isDark;
  final VoidCallback onTap;
  final VoidCallback onEdit;

  const ToolCard({
    super.key,
    required this.tool,
    this.isSelected = false,
    this.isDark = false,
    required this.onTap,
    required this.onEdit,
  });

  @override
  State<ToolCard> createState() => _ToolCardState();
}

class _ToolCardState extends State<ToolCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final typeColor = AppTheme.getToolTypeColor(widget.tool.toolType);
    final typeIcon = AppTheme.getToolTypeIcon(widget.tool.toolType);
    final decoration = AppTheme.cardDecoration(
      isDark: widget.isDark,
      isHovered: _isHovered,
      isSelected: widget.isSelected,
    );
    final textSecondary = Theme.of(context).textTheme.bodySmall!.color ??
        (widget.isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight);
    final textTertiary = widget.isDark ? AppTheme.textTertiaryDark : AppTheme.textTertiaryLight;

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          decoration: decoration,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    // Type icon
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: typeColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(typeIcon, color: typeColor, size: 20),
                    ),
                    const SizedBox(width: 12),
                    
                    // Name and type
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.tool.toolName,
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 2),
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: typeColor.withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  widget.tool.toolTypeLabel,
                                  style: GoogleFonts.inter(
                                    color: typeColor,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                'v${widget.tool.version}',
                                style: GoogleFonts.inter(fontSize: 11, fontWeight: FontWeight.w500, color: textTertiary),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    
                    // Edit button (on hover)
                    AnimatedOpacity(
                      opacity: _isHovered ? 1.0 : 0.0,
                      duration: const Duration(milliseconds: 150),
                      child: IconButton(
                        onPressed: widget.onEdit,
                        icon: const Icon(Icons.edit_outlined, size: 18),
                        color: AppTheme.textSecondaryDark,
                        tooltip: 'Edit',
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 12),
                
                // Description
                Expanded(
                  child: Text(
                    widget.tool.description,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w400,
                          color: Theme.of(context).textTheme.bodyMedium?.color?.withOpacity(0.9),
                        ),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                
                const SizedBox(height: 12),
                
                // Footer
                Row(
                  children: [
                    // Parameters count
                    Icon(
                      Icons.input,
                      size: 14,
                      color: textTertiary,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${widget.tool.parameters.length} params',
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                    const SizedBox(width: 16),
                    
                    // Timeout
                    Icon(
                      Icons.timer_outlined,
                      size: 14,
                      color: textTertiary,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '${widget.tool.timeoutS}s',
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                    
                    const Spacer(),
                    
                    // ID
                    Text(
                      widget.tool.id,
                      style: GoogleFonts.firaCode(
                        fontSize: 10,
                        color: textSecondary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

