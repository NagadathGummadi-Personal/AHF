import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Enterprise dual-theme with deep blue primary + teal accent.
class AppTheme {
  AppTheme._();

  // Brand / semantic
  static const Color primary = Color(0xFF0B4F9C);
  static const Color accent = Color(0xFF0FA3B1);
  static const Color success = Color(0xFF12805C);
  static const Color warning = Color(0xFFB26B00);
  static const Color error = Color(0xFFB3261E);
  static const Color info = Color(0xFF0F98D6);

  // Light neutrals
  static const Color bgLight = Color(0xFFF6F7FB);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color cardLight = Color(0xFFFFFFFF);
  static const Color borderLight = Color(0xFFE5E7EB);
  static const Color dividerLight = Color(0xFFE5E7EB);
  static const Color textPrimaryLight = Color(0xFF111827);
  static const Color textSecondaryLight = Color(0xFF4B5563);
  static const Color textTertiaryLight = Color(0xFF9CA3AF);

  // Dark neutrals
  static const Color bgDark = Color(0xFF0F172A);
  static const Color surfaceDark = Color(0xFF111827);
  static const Color cardDark = Color(0xFF161F2D);
  static const Color borderDark = Color(0xFF1F2937);
  static const Color dividerDark = Color(0xFF1F2937);
  static const Color textPrimaryDark = Color(0xFFE5E7EB);
  static const Color textSecondaryDark = Color(0xFF9CA3AF);
  static const Color textTertiaryDark = Color(0xFF6B7280);

  // Tool type colors
  static const Color functionColor = Color(0xFF0FA3B1);
  static const Color httpColor = Color(0xFF7C3AED);
  static const Color dbColor = Color(0xFFF59E0B);

  static TextStyle font(double size,
          {FontWeight weight = FontWeight.w400,
          Color? color,
          double? height,
          double? letterSpacing}) =>
      GoogleFonts.inter(
        fontSize: size,
        fontWeight: weight,
        color: color,
        height: height,
        letterSpacing: letterSpacing,
      );

  static TextTheme textTheme(Color p, Color s, Color t) => TextTheme(
        displayLarge: font(28, weight: FontWeight.w700, color: p, height: 1.2),
        displayMedium: font(24, weight: FontWeight.w700, color: p, height: 1.2),
        headlineMedium: font(20, weight: FontWeight.w600, color: p, height: 1.3),
        headlineSmall: font(18, weight: FontWeight.w600, color: p, height: 1.3),
        titleLarge: font(18, weight: FontWeight.w600, color: p, height: 1.3),
        titleMedium: font(16, weight: FontWeight.w600, color: p, height: 1.35),
        titleSmall: font(14, weight: FontWeight.w600, color: p, height: 1.35),
        bodyLarge: font(16, weight: FontWeight.w400, color: p, height: 1.5),
        bodyMedium: font(14, weight: FontWeight.w400, color: p, height: 1.5),
        bodySmall: font(12, weight: FontWeight.w400, color: s, height: 1.5),
        labelLarge: font(14, weight: FontWeight.w600, color: p, height: 1.3),
        labelMedium: font(12, weight: FontWeight.w500, color: s, height: 1.3),
        labelSmall: font(11,
            weight: FontWeight.w500, color: t, height: 1.3, letterSpacing: 0.4),
      );

  static InputDecorationTheme inputTheme({
    required Color fill,
    required Color border,
    required Color focus,
    required Color errorColor,
    required TextStyle label,
    required TextStyle hint,
    required TextStyle errorStyle,
  }) =>
      InputDecorationTheme(
        filled: true,
        fillColor: fill,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: focus, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: errorColor),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: errorColor, width: 2),
        ),
        labelStyle: label,
        hintStyle: hint,
        errorStyle: errorStyle,
      );

  static ButtonStyle elevated(Color bg, Color fg) => ElevatedButton.styleFrom(
        backgroundColor: bg,
        foregroundColor: fg,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: font(14, weight: FontWeight.w600, color: fg),
      );

  static ButtonStyle outlined(Color fg, Color border) => OutlinedButton.styleFrom(
        foregroundColor: fg,
        side: BorderSide(color: border),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: font(14, weight: FontWeight.w600, color: fg),
      );

  static ButtonStyle textBtn(Color fg) => TextButton.styleFrom(
        foregroundColor: fg,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        textStyle: font(14, weight: FontWeight.w600, color: fg),
      );

  static ThemeData lightTheme = _buildTheme(
    brightness: Brightness.light,
    background: bgLight,
    surface: surfaceLight,
    card: cardLight,
    border: borderLight,
    divider: dividerLight,
    textPrimary: textPrimaryLight,
    textSecondary: textSecondaryLight,
    textTertiary: textTertiaryLight,
  );

  static ThemeData darkTheme = _buildTheme(
    brightness: Brightness.dark,
    background: bgDark,
    surface: surfaceDark,
    card: cardDark,
    border: borderDark,
    divider: dividerDark,
    textPrimary: textPrimaryDark,
    textSecondary: textSecondaryDark,
    textTertiary: textTertiaryDark,
  );

  static ThemeData _buildTheme({
    required Brightness brightness,
    required Color background,
    required Color surface,
    required Color card,
    required Color border,
    required Color divider,
    required Color textPrimary,
    required Color textSecondary,
    required Color textTertiary,
  }) {
    final scheme = ColorScheme(
      brightness: brightness,
      primary: primary,
      onPrimary: Colors.white,
      secondary: accent,
      onSecondary: Colors.white,
      error: error,
      onError: Colors.white,
      background: background,
      onBackground: textPrimary,
      surface: surface,
      onSurface: textPrimary,
      tertiary: accent,
      onTertiary: Colors.white,
    );
    final txt = textTheme(textPrimary, textSecondary, textTertiary);

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        elevation: 0,
        titleTextStyle: txt.titleMedium,
        iconTheme: IconThemeData(color: textPrimary, size: 20),
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: border),
        ),
        margin: EdgeInsets.zero,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        elevation: 12,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        titleTextStyle: txt.titleMedium,
      ),
      dividerTheme: DividerThemeData(color: divider, thickness: 1, space: 1),
      inputDecorationTheme: inputTheme(
        fill: brightness == Brightness.light ? Colors.white : card,
        border: border,
        focus: primary,
        errorColor: error,
        label: txt.labelMedium!,
        hint: txt.bodyMedium!.copyWith(color: textTertiary),
        errorStyle: txt.bodySmall!.copyWith(color: error),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(style: elevated(primary, Colors.white)),
      outlinedButtonTheme: OutlinedButtonThemeData(style: outlined(textPrimary, border)),
      textButtonTheme: TextButtonThemeData(style: textBtn(primary)),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? primary : textTertiary,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected)
              ? primary.withOpacity(0.25)
              : border,
        ),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: primary,
        inactiveTrackColor: border,
        thumbColor: primary,
        overlayColor: primary.withOpacity(0.12),
        valueIndicatorColor: primary,
        valueIndicatorTextStyle: txt.labelMedium!.copyWith(color: Colors.white),
      ),
      iconTheme: IconThemeData(color: textSecondary, size: 20),
      textTheme: txt,
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: brightness == Brightness.light ? textPrimary : card,
          borderRadius: BorderRadius.circular(6),
        ),
        textStyle: txt.bodySmall!.copyWith(color: Colors.white),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: brightness == Brightness.light ? textPrimary : card,
        contentTextStyle: txt.bodyMedium!.copyWith(color: Colors.white),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        behavior: SnackBarBehavior.floating,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: brightness == Brightness.light ? surface : card,
        selectedColor: primary.withOpacity(0.12),
        labelStyle: txt.labelMedium!,
        side: BorderSide(color: border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: primary),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? primary : Colors.transparent,
        ),
        checkColor: WidgetStateProperty.all(Colors.white),
        side: BorderSide(color: border, width: 1.5),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
      ),
    );
  }

  static Color getToolTypeColor(String toolType) {
    switch (toolType.toLowerCase()) {
      case 'function':
        return functionColor;
      case 'http':
        return httpColor;
      case 'db':
      case 'database':
        return dbColor;
      default:
        return textTertiaryLight;
    }
  }

  static IconData getToolTypeIcon(String toolType) {
    switch (toolType.toLowerCase()) {
      case 'function':
        return Icons.code;
      case 'http':
        return Icons.http;
      case 'db':
      case 'database':
        return Icons.storage;
      default:
        return Icons.extension;
    }
  }

  static BoxDecoration cardDecoration({
    required bool isDark,
    bool isHovered = false,
    bool isSelected = false,
  }) {
    final border = isDark ? borderDark : borderLight;
    final base = isDark ? cardDark : cardLight;
    final shadowColor = isSelected ? primary : primary.withOpacity(0.08);
    return BoxDecoration(
      color: base,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(
        color: isSelected
            ? primary
            : isHovered
                ? primary.withOpacity(0.35)
                : border,
        width: isSelected ? 1.5 : 1,
      ),
      boxShadow: isHovered || isSelected
          ? [
              BoxShadow(
                color: shadowColor.withOpacity(0.18),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ]
          : null,
    );
  }

  static BoxDecoration sectionDecoration({required bool isDark}) {
    final border = isDark ? borderDark : borderLight;
    final surface = isDark ? cardDark : cardLight;
    return BoxDecoration(
      color: surface,
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: border),
    );
  }
}