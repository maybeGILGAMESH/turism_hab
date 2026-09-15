import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, radius, shadow, spacing, touch, type } from '../theme';

export function Icon({ name, size = 20, color = colors.ink, style }) {
  return <MaterialCommunityIcons name={name} size={size} color={color} style={style} />;
}

const BUTTON_VARIANTS = {
  primary: { bg: colors.amur, fg: colors.white, border: colors.amur },
  gold: { bg: colors.gold, fg: colors.white, border: colors.gold },
  ghost: { bg: colors.white, fg: colors.amur, border: colors.sky2 },
  success: { bg: colors.ok, fg: colors.white, border: colors.ok },
  danger: { bg: colors.white, fg: colors.bad, border: '#F0C9C4' },
};

export function Button({ title, icon, onPress, variant = 'primary', disabled, loading, style, compact, accessibilityLabel }) {
  const palette = BUTTON_VARIANTS[variant] || BUTTON_VARIANTS.primary;
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || title}
      accessibilityState={{ disabled: !!(disabled || loading) }}
      style={({ pressed }) => [
        styles.button,
        compact && styles.buttonCompact,
        { backgroundColor: palette.bg, borderColor: palette.border },
        (disabled || loading) && styles.disabled,
        pressed && styles.pressed,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={palette.fg} />
      ) : (
        <>
          {icon ? <Icon name={icon} size={compact ? 18 : 20} color={palette.fg} /> : null}
          {title ? (
            <Text style={[styles.buttonText, compact && styles.buttonTextCompact, { color: palette.fg }]} numberOfLines={1}>
              {title}
            </Text>
          ) : null}
        </>
      )}
    </Pressable>
  );
}

export function IconButton({ icon, onPress, label, color = colors.ink, style }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={4}
      style={({ pressed }) => [styles.iconButton, pressed && styles.pressed, style]}
    >
      <Icon name={icon} size={22} color={color} />
    </Pressable>
  );
}

export function Card({ children, style, onPress, accessibilityLabel }) {
  if (!onPress) return <View style={[styles.card, style]}>{children}</View>;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed, style]}
    >
      {children}
    </Pressable>
  );
}

const CHIP_TONES = {
  sky: { bg: colors.sky, fg: colors.amurDark },
  gold: { bg: colors.goldSoft, fg: colors.goldInk },
  ok: { bg: colors.okSoft, fg: colors.ok },
  bad: { bg: colors.badSoft, fg: colors.bad },
  white: { bg: colors.white, fg: colors.amurDark },
};

export function Chip({ icon, label, tone = 'sky', onPress, selected, style }) {
  const palette = selected ? { bg: colors.amur, fg: colors.white } : CHIP_TONES[tone] || CHIP_TONES.sky;
  const content = (
    <>
      {icon ? <Icon name={icon} size={15} color={palette.fg} /> : null}
      <Text style={[styles.chipText, { color: palette.fg }]} numberOfLines={2}>{label}</Text>
    </>
  );
  if (!onPress) return <View style={[styles.chip, { backgroundColor: palette.bg }, style]}>{content}</View>;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: !!selected }}
      style={({ pressed }) => [styles.chip, styles.chipTouch, { backgroundColor: palette.bg }, !selected && tone === 'white' && styles.chipBorder, pressed && styles.pressed, style]}
    >
      {content}
    </Pressable>
  );
}

export function Notice({ tone = 'warn', icon, children, style }) {
  const palette = tone === 'bad'
    ? { bg: colors.badSoft, fg: colors.bad, icon: 'alert-circle-outline' }
    : tone === 'ok'
      ? { bg: colors.okSoft, fg: colors.ok, icon: 'check-circle-outline' }
      : tone === 'info'
        ? { bg: colors.sky, fg: colors.amurDark, icon: 'information-outline' }
        : { bg: colors.goldSoft, fg: colors.goldInk, icon: 'alert-outline' };
  return (
    <View style={[styles.notice, { backgroundColor: palette.bg }, style]} accessibilityRole="alert">
      <Icon name={icon || palette.icon} size={20} color={palette.fg} />
      <Text style={[styles.noticeText, { color: palette.fg }]}>{children}</Text>
    </View>
  );
}

export function SectionTitle({ icon, children, style }) {
  return (
    <View style={[styles.sectionTitle, style]}>
      {icon ? <Icon name={icon} size={20} color={colors.amur} /> : null}
      <Text style={type.h2}>{children}</Text>
    </View>
  );
}

export function EmptyState({ icon = 'map-search-outline', title, text, children }) {
  return (
    <View style={styles.empty}>
      <View style={styles.emptyIcon}><Icon name={icon} size={30} color={colors.amur} /></View>
      <Text style={[type.h3, styles.centerText]}>{title}</Text>
      {text ? <Text style={[type.small, styles.centerText]}>{text}</Text> : null}
      {children}
    </View>
  );
}

export function Segmented({ options, value, onChange }) {
  return (
    <View style={styles.segmented} accessibilityRole="radiogroup">
      {options.map(option => {
        const active = option.value === value;
        return (
          <Pressable
            key={option.value}
            onPress={() => onChange(option.value)}
            accessibilityRole="radio"
            accessibilityState={{ checked: active }}
            style={[styles.segment, active && styles.segmentActive]}
          >
            {option.icon ? <Icon name={option.icon} size={18} color={active ? colors.amur : colors.muted} /> : null}
            <Text style={[styles.segmentText, active && styles.segmentTextActive]}>{option.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 48,
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
  },
  buttonCompact: { minHeight: touch, paddingHorizontal: spacing.md },
  buttonText: { fontSize: 16, fontWeight: '700', flexShrink: 1 },
  buttonTextCompact: { fontSize: 14 },
  disabled: { opacity: 0.5 },
  pressed: { opacity: 0.85 },
  iconButton: { width: touch, height: touch, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center' },
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.line,
    overflow: 'hidden',
    ...shadow,
  },
  cardPressed: { opacity: 0.95, transform: [{ scale: 0.995 }] },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: radius.pill,
    paddingHorizontal: 10,
    paddingVertical: 4,
    alignSelf: 'flex-start',
    maxWidth: '100%',
  },
  chipTouch: { minHeight: touch - 6, paddingHorizontal: spacing.md },
  chipBorder: { borderWidth: 1, borderColor: colors.sky2 },
  chipText: { fontSize: 13, fontWeight: '600', flexShrink: 1 },
  notice: { flexDirection: 'row', gap: spacing.sm, borderRadius: radius.md, padding: spacing.md, alignItems: 'flex-start' },
  noticeText: { flex: 1, fontSize: 14, lineHeight: 20 },
  sectionTitle: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, marginBottom: spacing.sm },
  empty: { alignItems: 'center', padding: spacing.xl, gap: spacing.sm },
  emptyIcon: { width: 64, height: 64, borderRadius: 32, backgroundColor: colors.sky, alignItems: 'center', justifyContent: 'center' },
  centerText: { textAlign: 'center' },
  segmented: { flexDirection: 'row', backgroundColor: colors.sky, borderRadius: radius.md, padding: 4, gap: 4 },
  segment: { flex: 1, minHeight: 40, borderRadius: 9, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  segmentActive: { backgroundColor: colors.white, ...shadow },
  segmentText: { fontSize: 14, fontWeight: '600', color: colors.muted },
  segmentTextActive: { color: colors.amur },
});
