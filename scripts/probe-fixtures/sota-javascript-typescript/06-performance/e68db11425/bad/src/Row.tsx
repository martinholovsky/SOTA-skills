export const Row = React.memo(function Row({ item }: { item: Item }) {
  const style = useMemo(() => ({ padding: 4 }), []);
  return <li style={style}>{item.name}</li>;
});
