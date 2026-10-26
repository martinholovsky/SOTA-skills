const style = { padding: 4 };
export function Row({ item }: { item: Item }) {
  return <li style={style}>{item.name}</li>;
}
