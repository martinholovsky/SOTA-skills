export function Search({ onSearch }: Props) {
  const run = debounce(onSearch, 300);
  return <input onChange={(e) => run(e.target.value)} />;
}
