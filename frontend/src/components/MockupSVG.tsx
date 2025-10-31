export function DashboardMockup() {
  return (
    <svg
      viewBox="0 0 800 600"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-auto animate-float"
    >
      {/* Background */}
      <rect width="800" height="600" fill="#0B1220" rx="20" />
      
      {/* Glow effect */}
      <defs>
        <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6366F1" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.1" />
        </linearGradient>
        <filter id="blur">
          <feGaussianBlur in="SourceGraphic" stdDeviation="10" />
        </filter>
      </defs>
      
      {/* Ambient glow */}
      <ellipse cx="400" cy="300" rx="300" ry="200" fill="url(#glow)" filter="url(#blur)" opacity="0.4" />
      
      {/* Main card */}
      <rect x="100" y="100" width="600" height="400" rx="16" fill="#111827" fillOpacity="0.85" stroke="white" strokeOpacity="0.1" strokeWidth="1" />
      
      {/* Header */}
      <rect x="120" y="120" width="560" height="60" rx="12" fill="#1F2937" fillOpacity="0.5" />
      <rect x="140" y="135" width="200" height="30" rx="8" fill="#6366F1" fillOpacity="0.3" />
      
      {/* Stats cards */}
      <g className="animate-slide-up">
        <rect x="120" y="200" width="170" height="120" rx="12" fill="#1F2937" fillOpacity="0.4" stroke="white" strokeOpacity="0.1" strokeWidth="1" />
        <rect x="140" y="220" width="50" height="8" rx="4" fill="#22C55E" fillOpacity="0.5" />
        <rect x="140" y="240" width="130" height="20" rx="6" fill="#E5E7EB" fillOpacity="0.3" />
        <rect x="140" y="270" width="100" height="12" rx="6" fill="#60A5FA" fillOpacity="0.4" />
      </g>
      
      <g className="animate-slide-up" style={{ animationDelay: '0.1s' }}>
        <rect x="315" y="200" width="170" height="120" rx="12" fill="#1F2937" fillOpacity="0.4" stroke="white" strokeOpacity="0.1" strokeWidth="1" />
        <rect x="335" y="220" width="50" height="8" rx="4" fill="#F59E0B" fillOpacity="0.5" />
        <rect x="335" y="240" width="130" height="20" rx="6" fill="#E5E7EB" fillOpacity="0.3" />
        <rect x="335" y="270" width="80" height="12" rx="6" fill="#60A5FA" fillOpacity="0.4" />
      </g>
      
      <g className="animate-slide-up" style={{ animationDelay: '0.2s' }}>
        <rect x="510" y="200" width="170" height="120" rx="12" fill="#1F2937" fillOpacity="0.4" stroke="white" strokeOpacity="0.1" strokeWidth="1" />
        <rect x="530" y="220" width="50" height="8" rx="4" fill="#EF4444" fillOpacity="0.5" />
        <rect x="530" y="240" width="130" height="20" rx="6" fill="#E5E7EB" fillOpacity="0.3" />
        <rect x="530" y="270" width="120" height="12" rx="6" fill="#60A5FA" fillOpacity="0.4" />
      </g>
      
      {/* Progress bars */}
      <g className="animate-scale-in" style={{ animationDelay: '0.3s' }}>
        <rect x="120" y="340" width="560" height="40" rx="12" fill="#1F2937" fillOpacity="0.4" />
        <rect x="130" y="350" width="400" height="8" rx="4" fill="white" fillOpacity="0.15" />
        <rect x="130" y="350" width="280" height="8" rx="4" fill="url(#progress-gradient)" />
        
        <rect x="130" y="365" width="300" height="8" rx="4" fill="white" fillOpacity="0.15" />
        <rect x="130" y="365" width="180" height="8" rx="4" fill="url(#progress-gradient)" />
      </g>
      
      <defs>
        <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#22C55E" />
          <stop offset="100%" stopColor="#16A34A" />
        </linearGradient>
      </defs>
      
      {/* Floating particles */}
      <circle cx="150" cy="150" r="2" fill="#6366F1" opacity="0.6" className="animate-pulse-slow" />
      <circle cx="650" cy="180" r="3" fill="#60A5FA" opacity="0.5" className="animate-pulse-slow" style={{ animationDelay: '0.5s' }} />
      <circle cx="200" cy="450" r="2" fill="#22C55E" opacity="0.4" className="animate-pulse-slow" style={{ animationDelay: '1s' }} />
    </svg>
  )
}

export function ExamMockup() {
  return (
    <svg
      viewBox="0 0 700 800"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-auto animate-slide-up"
    >
      {/* Background */}
      <rect width="700" height="800" fill="#0B1220" rx="20" />
      
      {/* Glow */}
      <defs>
        <linearGradient id="exam-glow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#6366F1" stopOpacity="0.2" />
          <stop offset="100%" stopColor="#60A5FA" stopOpacity="0.1" />
        </linearGradient>
      </defs>
      
      <ellipse cx="350" cy="400" rx="250" ry="300" fill="url(#exam-glow)" opacity="0.3" />
      
      {/* Paper card */}
      <rect x="50" y="50" width="600" height="700" rx="16" fill="#111827" fillOpacity="0.9" stroke="white" strokeOpacity="0.1" strokeWidth="1.5" />
      
      {/* Title */}
      <rect x="80" y="80" width="300" height="40" rx="8" fill="#6366F1" fillOpacity="0.2" />
      <rect x="100" y="90" width="200" height="20" rx="6" fill="#E5E7EB" fillOpacity="0.5" />
      
      {/* Questions */}
      {[0, 1, 2, 3].map((i) => (
        <g key={i} className="animate-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
          <rect x="80" y={150 + i * 150} width="540" height="130" rx="12" fill="#1F2937" fillOpacity="0.5" stroke="white" strokeOpacity="0.08" strokeWidth="1" />
          
          {/* Question text */}
          <rect x="100" y={170 + i * 150} width="400" height="12" rx="6" fill="#E5E7EB" fillOpacity="0.4" />
          <rect x="100" y={190 + i * 150} width="350" height="10" rx="5" fill="#E5E7EB" fillOpacity="0.3" />
          
          {/* Options */}
          <rect x="110" y={215 + i * 150} width="480" height="18" rx="9" fill="white" fillOpacity="0.05" />
          <circle cx="125" cy={224 + i * 150} r="6" stroke="#6366F1" strokeWidth="2" fill="none" />
          <rect x="145" y={218 + i * 150} width="200" height="12" rx="6" fill="#E5E7EB" fillOpacity="0.3" />
          
          <rect x="110" y={243 + i * 150} width="480" height="18" rx="9" fill="white" fillOpacity="0.05" />
          <circle cx="125" cy={252 + i * 150} r="6" stroke="#60A5FA" strokeWidth="2" fill="none" />
          <rect x="145" y={246 + i * 150} width="180" height="12" rx="6" fill="#E5E7EB" fillOpacity="0.3" />
        </g>
      ))}
      
      {/* Submit button */}
      <rect x="250" y="720" width="200" height="50" rx="12" fill="url(#button-gradient)" className="animate-pulse-slow" />
      <rect x="290" y="735" width="120" height="20" rx="6" fill="white" fillOpacity="0.9" />
      
      <defs>
        <linearGradient id="button-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#6366F1" />
          <stop offset="100%" stopColor="#60A5FA" />
        </linearGradient>
      </defs>
    </svg>
  )
}

export function AnalyticsMockup() {
  return (
    <svg
      viewBox="0 0 800 500"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-auto"
    >
      {/* Background */}
      <rect width="800" height="500" fill="#0B1220" rx="20" />
      
      {/* Card */}
      <rect x="50" y="50" width="700" height="400" rx="16" fill="#111827" fillOpacity="0.85" stroke="white" strokeOpacity="0.1" strokeWidth="1" />
      
      {/* Chart bars */}
      {[
        { x: 100, height: 200, delay: 0 },
        { x: 180, height: 280, delay: 0.1 },
        { x: 260, height: 150, delay: 0.2 },
        { x: 340, height: 320, delay: 0.3 },
        { x: 420, height: 240, delay: 0.4 },
        { x: 500, height: 300, delay: 0.5 },
        { x: 580, height: 180, delay: 0.6 },
      ].map((bar, i) => (
        <g key={i} className="animate-slide-up" style={{ animationDelay: `${bar.delay}s` }}>
          <rect x={bar.x} y={400 - bar.height} width="50" height={bar.height} rx="6" fill="url(#bar-gradient)" opacity="0.8" />
        </g>
      ))}
      
      {/* Grid lines */}
      {[0, 1, 2, 3, 4].map((i) => (
        <line key={i} x1="80" y1={100 + i * 60} x2="720" y2={100 + i * 60} stroke="white" strokeOpacity="0.05" strokeWidth="1" />
      ))}
      
      <defs>
        <linearGradient id="bar-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#6366F1" />
          <stop offset="100%" stopColor="#60A5FA" />
        </linearGradient>
      </defs>
    </svg>
  )
}
