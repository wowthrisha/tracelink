const { useRef, useEffect } = React;

export function LaserPointer({ active }) {
  const dotRef = useRef(null);
  useEffect(() => {
    if (!active) return;
    const move = e => {
      if (dotRef.current) {
        dotRef.current.style.transform = `translate(${e.clientX - 10}px, ${e.clientY - 10}px)`;
        dotRef.current.style.opacity = '1';
      }
    };
    document.addEventListener('mousemove', move, { passive: true });
    return () => document.removeEventListener('mousemove', move);
  }, [active]);
  if (!active) return null;
  return (
    <div ref={dotRef} style={{
      position: 'fixed', top: 0, left: 0,
      width: 20, height: 20, borderRadius: '50%',
      background: 'radial-gradient(circle, rgba(255,60,60,1) 0%, rgba(255,60,60,0.7) 35%, rgba(255,60,60,0.15) 70%, transparent 100%)',
      boxShadow: '0 0 8px 3px rgba(255,50,50,0.55), 0 0 18px 6px rgba(255,50,50,0.25)',
      pointerEvents: 'none', zIndex: 9999,
      transform: 'translate(-9999px,-9999px)',
      willChange: 'transform',
    }} />
  );
}
