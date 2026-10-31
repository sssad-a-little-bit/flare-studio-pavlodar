export function ArrowIcon({ diagonal = false }: { diagonal?: boolean }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true" style={diagonal ? { transform: 'rotate(-45deg)' } : undefined}><path d="M4 12h15M13 5l7 7-7 7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
export function PhoneIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M8.2 3H4.7C3.8 3 3 3.8 3.1 4.7c.8 8.5 7.7 15.4 16.2 16.2.9.1 1.7-.7 1.7-1.6v-3.5l-4.5-1.7-2 2a14.1 14.1 0 0 1-6.6-6.6l2-2L8.2 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></svg>;
}
export function CopyIcon() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="8" y="8" width="12" height="13" rx="2" stroke="currentColor" strokeWidth="1.5" /><path d="M15 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h3" stroke="currentColor" strokeWidth="1.5" /></svg>;
}
