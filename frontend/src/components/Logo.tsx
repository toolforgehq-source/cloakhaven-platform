interface LogoProps {
  size?: number;
  className?: string;
}

export default function Logo({ size = 32, className = '' }: LogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 512 512"
      width={size}
      height={size}
      className={className}
    >
      <defs>
        <linearGradient id="logo-g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: '#818CF8' }} />
          <stop offset="100%" style={{ stopColor: '#4F46E5' }} />
        </linearGradient>
      </defs>
      <path d="M256 48 L432 120 C432 120 440 300 256 464 C72 300 80 120 80 120 Z" fill="url(#logo-g)" />
      <path d="M256 80 L406 140 C406 140 413 290 256 432 C99 290 106 140 106 140 Z" fill="#0F172A" />
      <ellipse cx="256" cy="230" rx="100" ry="60" fill="none" stroke="#818CF8" strokeWidth="6" />
      <circle cx="256" cy="230" r="35" fill="#6366F1" />
      <circle cx="256" cy="230" r="16" fill="#0F172A" />
      <circle cx="246" cy="222" r="6" fill="white" opacity="0.7" />
    </svg>
  );
}
