export function Button({ onClick }: { onClick: () => void }) {
  return <button className="btn" onClick={onClick}>Save</button>;
}
