export const R = ({ id, onDelete }) => (
  <button aria-label={`Delete invoice ${id}`} onClick={onDelete}>x</button>
);
