export const categories = ['u6', 'u8', 'u10', 'u12', 'u14', 'u16', 'u18', 'libre'];
export const branches = ['varonil', 'femenil', 'mixto'];
export type Division = {branch: string; category: string};
export function normalizeDivision(division: Division): Division {
  return ['u8', 'u10', 'u12'].includes(division.category) ? {...division, branch: 'mixto'} : division;
}
