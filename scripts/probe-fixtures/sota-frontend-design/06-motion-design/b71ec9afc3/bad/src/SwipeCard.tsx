export function SwipeCard({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div className="card" onPointerMove={(e) => track(e.clientX)} onPointerUp={release}>
      <slot />
    </div>
  );
}
