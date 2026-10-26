export function Header() {
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const onScroll = () => setStuck(document.documentElement.scrollTop > 64);
    window.addEventListener('scroll', onScroll);
  }, []);
  return <header data-stuck={stuck} />;
}
