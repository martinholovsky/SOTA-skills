export function Header() {
  const sentinel = useRef<HTMLDivElement>(null);
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => setStuck(!e?.isIntersecting));
    if (sentinel.current) io.observe(sentinel.current);
    return () => io.disconnect();
  }, []);
  return <><div ref={sentinel} /><header data-stuck={stuck} /></>;
}
