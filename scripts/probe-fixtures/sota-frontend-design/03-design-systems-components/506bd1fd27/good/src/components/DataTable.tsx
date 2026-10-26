export interface DataTableProps {
  rows: Row[];
}

export const Dense = ({ children }: { children: React.ReactNode }) => (
  <div data-density="compact">{children}</div>
);
