export function Search({ onSearch }: Props) {
  const run = useMemo(() => debounce(onSearch, 300), [onSearch]);
  return <input onChange={(e) => run(e.target.value)} />;
}
