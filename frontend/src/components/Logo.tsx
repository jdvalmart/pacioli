export function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      className={className}
      role="img"
      aria-label="Pacioli"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="pacioli-gold" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FFDD5C" />
          <stop offset="1" stopColor="#F4B400" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="14" fill="url(#pacioli-gold)" />
      <rect
        x="1.25"
        y="1.25"
        width="45.5"
        height="45.5"
        rx="12.75"
        fill="none"
        stroke="#000000"
        strokeOpacity="0.08"
        strokeWidth="1.5"
      />
      {/* Book: the Bible for the friar, the ledger for the accountant */}
      <rect
        x="13"
        y="11"
        width="22"
        height="26"
        rx="3.5"
        fill="#FFF9E6"
        stroke="#3B2C00"
        strokeWidth="2.6"
      />
      <path d="M18.6 11v26" stroke="#3B2C00" strokeWidth="2.6" />
      {/* Cross */}
      <path
        d="M26 16.8v12M21.4 22.4h9.2"
        stroke="#3B2C00"
        strokeWidth="2.6"
        strokeLinecap="round"
      />
    </svg>
  )
}
