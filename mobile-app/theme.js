import { Platform } from 'react-native';

export const colors = {
  amur: '#0B4F7C',
  amurDark: '#073654',
  amur600: '#0E6399',
  sky: '#E8F3FA',
  sky2: '#CFE6F3',
  gold: '#C8962E',
  goldSoft: '#FBF3E0',
  goldInk: '#7A5712',
  ink: '#14212B',
  muted: '#5A6B78',
  line: '#D9E4EC',
  bg: '#F6F9FB',
  card: '#FFFFFF',
  white: '#FFFFFF',
  ok: '#1E7A4F',
  okSoft: '#E3F2EA',
  warn: '#B06A12',
  bad: '#B3261E',
  badSoft: '#FBE9E7',
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 8, md: 12, lg: 16, xl: 20, pill: 999 };
export const touch = 44;

export const type = {
  title: { fontSize: 22, lineHeight: 28, fontWeight: '700', color: colors.ink },
  h2: { fontSize: 18, lineHeight: 24, fontWeight: '700', color: colors.amurDark },
  h3: { fontSize: 16, lineHeight: 22, fontWeight: '700', color: colors.ink },
  body: { fontSize: 15, lineHeight: 22, color: colors.ink },
  small: { fontSize: 13, lineHeight: 18, color: colors.muted },
  label: { fontSize: 12, lineHeight: 16, fontWeight: '600', color: colors.muted },
};

export const shadow = Platform.select({
  ios: { shadowColor: colors.amurDark, shadowOpacity: 0.08, shadowRadius: 10, shadowOffset: { width: 0, height: 4 } },
  android: { elevation: 2 },
  default: { boxShadow: '0 4px 16px rgba(7, 54, 84, 0.08)' },
});

export const CATEGORY_LABELS = {
  architecture: 'Архитектура',
  engineering: 'Инженерия',
  museum: 'Музей',
  religion: 'Храм',
  monument: 'Памятник',
  memorial: 'Мемориал',
  urban_space: 'Город',
  culture: 'Культура',
  archaeology: 'Археология',
  ethnography: 'Этнография',
  nature: 'Природа',
};

export function formatMinutes(value) {
  const minutes = Math.round(Number(value) || 0);
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours >= 48) {
    const days = Math.floor(hours / 24);
    const h = hours % 24;
    return h ? `${days} дн ${h} ч` : `${days} дн`;
  }
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
}

export function formatKm(value) {
  const km = Number(value) || 0;
  return km < 0.1 ? '<0,1' : String(km).replace('.', ',');
}

export function formatRange(range) {
  if (!range) return '';
  return range.min === range.max ? formatMinutes(range.min) : `${formatMinutes(range.min)} – ${formatMinutes(range.max)}`;
}
