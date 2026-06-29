const { useRef, useEffect } = React;

export function RectMagnifier({ active, imgSrc, pageContainerRef }) {
  const MAG_W = 272, MAG_H = 180, SCALE = 2.5;
  const magnRef = useRef(null);

  useEffect(() => {
    if (!active || !pageContainerRef?.current) return;
    const container = pageContainerRef.current;

    const move = e => {
      const mag = magnRef.current;
      if (!mag || !imgSrc) return;
      const imgEl = container.querySelector('img[alt]');
      if (!imgEl) return;
      const imgRect = imgEl.getBoundingClientRect();
      const cx = e.clientX - imgRect.left;
      const cy = e.clientY - imgRect.top;
      if (cx < 0 || cy < 0 || cx > imgRect.width || cy > imgRect.height) {
        mag.style.opacity = '0'; return;
      }
      let mx = e.clientX + 24;
      let my = e.clientY - MAG_H / 2;
      if (mx + MAG_W > window.innerWidth - 8) mx = e.clientX - MAG_W - 24;
      if (my < 8) my = 8;
      if (my + MAG_H > window.innerHeight - 8) my = window.innerHeight - MAG_H - 8;
      mag.style.transform = `translate(${mx}px, ${my}px)`;
      const bgX = -(cx * SCALE - MAG_W / 2);
      const bgY = -(cy * SCALE - MAG_H / 2);
      mag.style.backgroundImage = `url("${imgSrc}")`;
      mag.style.backgroundSize = `${imgRect.width * SCALE}px ${imgRect.height * SCALE}px`;
      mag.style.backgroundPosition = `${bgX}px ${bgY}px`;
      mag.style.opacity = '1';
    };
    const leave = () => { if (magnRef.current) magnRef.current.style.opacity = '0'; };

    container.addEventListener('mousemove', move, { passive: true });
    container.addEventListener('mouseleave', leave, { passive: true });
    return () => {
      container.removeEventListener('mousemove', move);
      container.removeEventListener('mouseleave', leave);
    };
  }, [active, imgSrc, pageContainerRef]);

  if (!active) return null;
  return (
    <div ref={magnRef} style={{
      position: 'fixed', top: 0, left: 0, width: MAG_W, height: MAG_H,
      borderRadius: 8, overflow: 'hidden',
      border: '1.5px solid rgba(90,200,208,0.45)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.72), 0 0 0 1px rgba(90,200,208,0.12)',
      backgroundRepeat: 'no-repeat',
      opacity: 0, pointerEvents: 'none', zIndex: 1200,
      willChange: 'transform, opacity, background-position',
      transform: 'translate(-9999px,-9999px)',
      transition: 'opacity .08s',
    }}>
      <div style={{
        position: 'absolute', bottom: 6, right: 8, pointerEvents: 'none',
        fontFamily: 'ui-monospace,monospace', fontSize: 9, letterSpacing: '0.06em',
        color: 'rgba(90,200,208,0.9)', background: 'rgba(6,8,9,0.78)',
        padding: '2px 7px', borderRadius: 3,
        border: '1px solid rgba(90,200,208,0.22)',
      }}>2.5× ZOOM</div>
    </div>
  );
}
