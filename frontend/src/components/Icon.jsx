const paths = {
  upload: <><path d="M12 16V4m-4 4 4-4 4 4"/><path d="M4 15v5h16v-5"/></>,
  file: <><path d="M14 3H5v18h14V8Z"/><path d="M14 3v6h5M8 13h8M8 17h6"/></>,
  spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/><path d="M20 2v4m-2-2h4"/></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></>,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
  down: <path d="m6 9 6 6 6-6"/>,
  close: <path d="m6 6 12 12M6 18 18 6"/>,
  settings: <><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor" stroke="none"/><circle cx="15" cy="17" r="3" fill="currentColor" stroke="none"/></>,
  pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></>,
  briefcase: <><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V3h8v4M3 12c6 3 12 3 18 0M12 12v4"/></>,
  building: <><path d="M4 21V5l12-3v19M16 9h4v12M2 21h20M8 7h4M8 11h4M8 15h4M9 21v-3h3v3"/></>,
  export: <><path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/></>,
  external: <><path d="M14 3h7v7m0-7L11 13M10 4H3v17h17v-7"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  pause: <path d="M8 5v14M16 5v14"/>,
};
export default function Icon({ name, size = 18, ...props }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.file}</svg>;
}
