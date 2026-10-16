import { useEffect, useState, useRef, useMemo } from "react";
import type { ThemeMode, MotionLevel } from "../domain/contracts";

export interface HubPhotoItem {
  id: string;
  // TODO: Thay thế src bằng đường dẫn ảnh chụp thực tế khi tải lên (ví dụ: /photos/hub-ton-that-dam.jpg)
  src: string;
  caption: string;
  focalPoint: string;
  subtitle?: string;
}

// Mảng cấu hình ảnh HUB và chú thích cơ sở dễ dàng chỉnh sửa hoặc cập nhật đường dẫn ảnh
export const HUB_PHOTO_CONFIG: HubPhotoItem[] = [
  {
    id: "ton-that-dam",
    // TODO: Thay bằng đường dẫn ảnh chụp thực tế cơ sở 36 Tôn Thất Đạm, Quận 1
    src: "/photos/hub-ton-that-dam.jpg",
    caption: "HUB · Cơ sở Tôn Thất Đạm (Trụ sở chính)",
    subtitle: "Di sản kiến trúc tài chính - ngân hàng trung tâm TP.HCM",
    focalPoint: "center 42%"
  },
  {
    id: "ham-nghi",
    // TODO: Thay bằng đường dẫn ảnh chụp thực tế cơ sở 39 Hàm Nghi, Quận 1
    src: "/photos/hub-ham-nghi.jpg",
    caption: "HUB · Cơ sở Hàm Nghi",
    subtitle: "Trung tâm đào tạo chất lượng cao & công nghệ tài chính",
    focalPoint: "center 50%"
  },
  {
    id: "thu-duc",
    // TODO: Thay bằng đường dẫn ảnh chụp thực tế cơ sở 56 Hoàng Diệu 2, TP. Thủ Đức
    src: "/photos/hub-thu-duc.jpg",
    caption: "HUB · Cơ sở Thủ Đức",
    subtitle: "Khuôn viên đào tạo học thuật rộng lớn & giảng đường hiện đại",
    focalPoint: "center 40%"
  },
  {
    id: "sinh-vien",
    // TODO: Thay bằng đường dẫn ảnh sinh viên HUB trong giờ thực hành thẩm định
    src: "/photos/hub-sinh-vien.jpg",
    caption: "Sinh viên HUB · Thế hệ Tài chính - Công nghệ",
    subtitle: "Thẩm định tín dụng xác minh · Tư duy định lượng & quản trị rủi ro",
    focalPoint: "center 38%"
  },
  {
    id: "thu-vien",
    // TODO: Thay bằng đường dẫn ảnh thư viện số HUB
    src: "/photos/hub-thu-vien.jpg",
    caption: "Thư viện HUB · Không gian Tri thức & Dữ liệu số",
    subtitle: "Hạ tầng nghiên cứu dữ liệu, kinh tế lượng và ngân hàng số",
    focalPoint: "center 48%"
  }
];

interface AmbientBackgroundProps {
  theme: ThemeMode;
  motionLevel?: MotionLevel;
  /** Đường dẫn logo watermark (bản Streamlit truyền data URI). */
  logoSrc?: string;
}

export function AmbientBackground({ theme, motionLevel = "full", logoSrc = "/hub-logo-transparent.png" }: AmbientBackgroundProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [prevIndex, setPrevIndex] = useState<number | null>(null);
  const [isCrossfading, setIsCrossfading] = useState(false);
  const [failedImages, setFailedImages] = useState<Record<string, boolean>>({});
  const [isMobile, setIsMobile] = useState(false);
  const [isTabHidden, setIsTabHidden] = useState(false);

  // Parallax state with smooth lerping (max 8-12px)
  const targetOffsetRef = useRef({ x: 0, y: 0 });
  const currentOffsetRef = useRef({ x: 0, y: 0 });
  const [parallaxOffset, setParallaxOffset] = useState({ x: 0, y: 0 });
  const animFrameRef = useRef<number | null>(null);

  // Detect mobile viewport < 768px
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile, { passive: true });
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Detect tab visibility to pause animations and intervals
  useEffect(() => {
    const handleVisibility = () => {
      setIsTabHidden(document.hidden);
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  // Preload next image in sequence
  useEffect(() => {
    const nextIdx = (activeIndex + 1) % HUB_PHOTO_CONFIG.length;
    const nextPhoto = HUB_PHOTO_CONFIG[nextIdx];
    if (nextPhoto?.src) {
      const img = new Image();
      img.src = nextPhoto.src;
    }
  }, [activeIndex]);

  // Photo reel crossfade timer: 13 seconds per slide (Ken Burns motion lasts the duration)
  useEffect(() => {
    if (motionLevel === "off" || motionLevel === "light" || isTabHidden) {
      return;
    }

    const timer = setInterval(() => {
      setPrevIndex(activeIndex);
      setIsCrossfading(true);
      setActiveIndex((prev) => (prev + 1) % HUB_PHOTO_CONFIG.length);

      // Reset crossfading after transition time (1.6s)
      const fadeTimer = setTimeout(() => {
        setIsCrossfading(false);
        setPrevIndex(null);
      }, 1600);

      return () => clearTimeout(fadeTimer);
    }, 13000);

    return () => clearInterval(timer);
  }, [activeIndex, motionLevel, isTabHidden]);

  // Parallax mouse move listener with lerp damping (active only in 'full' mode and desktop)
  useEffect(() => {
    if (motionLevel !== "full" || isMobile || isTabHidden) {
      setParallaxOffset({ x: 0, y: 0 });
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) return;

    const handleMouseMove = (e: MouseEvent) => {
      // Maximum 10px translation for subtle institutional depth
      const normX = (e.clientX / window.innerWidth - 0.5) * 2;
      const normY = (e.clientY / window.innerHeight - 0.5) * 2;
      targetOffsetRef.current = {
        x: normX * 10,
        y: normY * 10
      };
    };

    const handleScroll = () => {
      const scrollY = window.scrollY;
      const maxScroll = 600;
      const normScrollY = Math.min(scrollY / maxScroll, 1);
      targetOffsetRef.current.y = targetOffsetRef.current.y + normScrollY * -6;
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("scroll", handleScroll, { passive: true });

    // Smooth lerp loop (damping ~0.06 for calm, non-jittery institutional feel)
    const updateLerp = () => {
      const target = targetOffsetRef.current;
      const current = currentOffsetRef.current;

      const dx = target.x - current.x;
      const dy = target.y - current.y;

      if (Math.abs(dx) > 0.05 || Math.abs(dy) > 0.05) {
        current.x += dx * 0.06;
        current.y += dy * 0.06;
        setParallaxOffset({
          x: Math.round(current.x * 100) / 100,
          y: Math.round(current.y * 100) / 100
        });
      }

      animFrameRef.current = requestAnimationFrame(updateLerp);
    };

    animFrameRef.current = requestAnimationFrame(updateLerp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("scroll", handleScroll);
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [motionLevel, isMobile, isTabHidden]);

  const handleImageError = (id: string) => {
    setFailedImages((prev) => ({ ...prev, [id]: true }));
  };

  const activePhoto = HUB_PHOTO_CONFIG[activeIndex];

  // Ràng buộc 4: Tối đa 2 ảnh nằm trong DOM cùng lúc (ảnh hiện tại + ảnh kế tiếp/trước đó khi chuyển)
  const renderedSlides = useMemo(() => {
    if (motionLevel === "off") {
      return [];
    }
    if (motionLevel === "light") {
      // In light mode, render only 1 static image
      return [{ item: HUB_PHOTO_CONFIG[0], role: "active" as const, index: 0 }];
    }
    const slides: { item: HubPhotoItem; role: "active" | "previous"; index: number }[] = [
      { item: activePhoto, role: "active", index: activeIndex }
    ];
    if (isCrossfading && prevIndex !== null && prevIndex !== activeIndex) {
      slides.unshift({
        item: HUB_PHOTO_CONFIG[prevIndex],
        role: "previous",
        index: prevIndex
      });
    }
    return slides;
  }, [activePhoto, activeIndex, prevIndex, isCrossfading, motionLevel]);

  return (
    <div
      className={`cl-ambient-bg cl-ambient-bg--${motionLevel}${isTabHidden ? " is-tab-paused" : ""}`}
      aria-hidden="true"
      data-theme={theme}
      data-motion={motionLevel}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: -1,
        pointerEvents: "none",
        overflow: "hidden"
      }}
    >
      {/* L0 – Canvas Base (styled via CSS token var(--cl-canvas)) */}
      <div className="cl-ambient-bg__canvas" />

      {/* L1 – HUB photo reel with Ken Burns & crossfade (Max 2 images in DOM) */}
      {motionLevel !== "off" && (
        <div
          className="cl-ambient-bg__photo-reel"
          style={{
            transform:
              motionLevel === "full" && !isMobile
                ? `translate3d(${parallaxOffset.x}px, ${parallaxOffset.y}px, 0)`
                : "none"
          }}
        >
          {renderedSlides.map(({ item, role, index }) => {
            const isActive = role === "active";
            const isError = failedImages[item.id];
            const kenBurnsVariant = index % 4; // Alternate pan & zoom directions

            return (
              <div
                key={`${item.id}-${role}`}
                className={`cl-ambient-slide${isActive ? " is-active" : " is-exiting"}`}
                style={{
                  zIndex: isActive ? 2 : 1
                }}
              >
                {/* Inner wrapper that performs Ken Burns */}
                <div
                  className={`cl-ambient-slide__motion cl-ambient-slide__motion--dir-${kenBurnsVariant}${
                    motionLevel === "light" ? " is-static" : ""
                  }`}
                  style={{
                    transformOrigin: item.focalPoint
                  }}
                >
                  {!isError ? (
                    <img
                      src={item.src}
                      alt=""
                      className="cl-ambient-slide__img"
                      style={{ objectPosition: item.focalPoint }}
                      loading="lazy"
                      decoding="async"
                      onError={() => handleImageError(item.id)}
                    />
                  ) : (
                    /* Abstract institutional duotone architectural vector composition */
                    <ArchitecturalNavyPlaceholder
                      id={item.id}
                      title={item.caption}
                      variant={kenBurnsVariant}
                    />
                  )}
                </div>

                {/* Duotone navy overlay for brand fidelity */}
                <div className="cl-ambient-slide__duotone" />
              </div>
            );
          })}
        </div>
      )}

      {/* L2 – Aurora gradient: 2-3 organic blurred drifting meshes (1 mesh on mobile) */}
      {motionLevel !== "off" && (
        <div
          className={`cl-ambient-bg__aurora${motionLevel === "light" ? " is-static" : ""}`}
          style={{
            transform:
              motionLevel === "full" && !isMobile
                ? `translate3d(${parallaxOffset.x * 1.3}px, ${parallaxOffset.y * 1.3}px, 0)`
                : "none"
          }}
        >
          <div className="cl-aurora-blob cl-aurora-blob--1" />
          {!isMobile && <div className="cl-aurora-blob cl-aurora-blob--2" />}
          {!isMobile && motionLevel === "full" && <div className="cl-aurora-blob cl-aurora-blob--3" />}
        </div>
      )}

      {/* L3 – Texture: fine subtle grid + static CreditLens watermark */}
      <div className="cl-ambient-bg__texture">
        <svg className="cl-texture-grid" width="100%" height="100%">
          <defs>
            <pattern
              id="cl-ambient-grid-pattern"
              width="40"
              height="40"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="currentColor"
                strokeWidth="0.75"
                strokeDasharray="2, 6"
              />
              <circle cx="40" cy="40" r="0.75" fill="currentColor" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#cl-ambient-grid-pattern)" />
        </svg>

        {/* Static CreditLens & HUB watermark at bottom-right corner */}
        <div className="cl-ambient-watermark">
          <img
            src={logoSrc}
            alt=""
            className="cl-ambient-watermark__img"
            onError={(e) => {
              (e.target as HTMLElement).style.display = "none";
            }}
          />
        </div>
      </div>

      {/* L4 – Readability scrim: gradient from canvas ensuring text contrast */}
      <div className="cl-ambient-bg__scrim" />

      {/* Caption: Subtle, quiet editorial label for the active reel in bottom-left */}
      {motionLevel !== "off" && (
        <div className="cl-ambient-caption" key={activePhoto.id}>
          <span className="cl-ambient-caption__dot" aria-hidden="true" />
          <div className="cl-ambient-caption__text">
            <strong className="cl-ambient-caption__title">{activePhoto.caption}</strong>
            {activePhoto.subtitle ? (
              <span className="cl-ambient-caption__sub">{activePhoto.subtitle}</span>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * ArchitecturalNavyPlaceholder:
 * When photographic files are pending upload, this generates an elegant,
 * institutional vector composition featuring HUB neoclassical pillars,
 * banking grids, and credit lens geometric vectors in brand navy.
 */
function ArchitecturalNavyPlaceholder({
  id,
  title,
  variant
}: {
  id: string;
  title: string;
  variant: number;
}) {
  return (
    <div className={`cl-ambient-placeholder cl-ambient-placeholder--${variant}`}>
      <svg
        className="cl-ambient-placeholder__svg"
        viewBox="0 0 1600 900"
        preserveAspectRatio="xMidYMid slice"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id={`grad-sky-${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#172A59" stopOpacity="0.45" />
            <stop offset="60%" stopColor="#203469" stopOpacity="0.30" />
            <stop offset="100%" stopColor="#0B1734" stopOpacity="0.60" />
          </linearGradient>
          <linearGradient id={`grad-pillar-${id}`} x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#203469" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#b4c5ff" stopOpacity="0.1" />
          </linearGradient>
          <linearGradient id={`grad-crimson-${id}`} x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#A71B28" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#A71B28" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Atmospheric field */}
        <rect width="1600" height="900" fill={`url(#grad-sky-${id})`} />

        {/* Geometric Perspective / Architectural Horizon */}
        <g opacity="0.22" stroke="currentColor" strokeWidth="1">
          {/* Vanishing Lines */}
          <line x1="0" y1="580" x2="1600" y2="580" strokeDasharray="6,6" />
          <line x1="800" y1="580" x2="0" y2="900" />
          <line x1="800" y1="580" x2="350" y2="900" />
          <line x1="800" y1="580" x2="700" y2="900" />
          <line x1="800" y1="580" x2="900" y2="900" />
          <line x1="800" y1="580" x2="1250" y2="900" />
          <line x1="800" y1="580" x2="1600" y2="900" />

          {/* Concentric risk radius rings */}
          <circle cx="800" cy="580" r="180" fill="none" strokeDasharray="4,8" />
          <circle cx="800" cy="580" r="340" fill="none" strokeDasharray="3,10" />
          <circle cx="800" cy="580" r="520" fill="none" strokeDasharray="2,14" />
        </g>

        {/* Neoclassical Facade: Neoclassical Pillars (Di sản HUB) */}
        <g opacity="0.18" fill="currentColor">
          <path d="M 520 380 L 800 290 L 1080 380 Z" />
          <rect x="500" y="380" width="600" height="24" rx="2" />
          <rect x="530" y="404" width="540" height="12" />

          <rect x="560" y="416" width="36" height="190" rx="3" fill={`url(#grad-pillar-${id})`} />
          <rect x="640" y="416" width="36" height="190" rx="3" fill={`url(#grad-pillar-${id})`} />
          <rect x="720" y="416" width="36" height="190" rx="3" fill={`url(#grad-pillar-${id})`} />
          <rect x="844" y="416" width="36" height="190" rx="3" fill={`url(#grad-pillar-${id})`} />
          <rect x="924" y="416" width="36" height="190" rx="3" fill={`url(#grad-pillar-${id})`} />
          <rect x="1004" y="416" width="36" height="190" rx="3" fill={`url(#grad-pillar-${id})`} />

          <rect x="480" y="606" width="640" height="18" rx="2" />
          <rect x="460" y="624" width="680" height="14" rx="2" />
        </g>

        {/* Crimson Accent Flare */}
        <circle cx="1280" cy="240" r="280" fill={`url(#grad-crimson-${id})`} />

        {/* Institutional Monogram Watermark */}
        <text
          x="1420"
          y="840"
          fill="currentColor"
          opacity="0.14"
          fontSize="48"
          fontWeight="800"
          letterSpacing="4"
          textAnchor="end"
          fontFamily="'Be Vietnam Pro', sans-serif"
        >
          ĐÁNH GIÁ TÍN DỤNG VAY
        </text>
      </svg>
    </div>
  );
}
