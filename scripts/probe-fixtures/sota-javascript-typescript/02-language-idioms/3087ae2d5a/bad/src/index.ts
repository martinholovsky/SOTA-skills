export const byId = (items: Item[]) =>
  items.reduce((acc, it) => ({ ...acc, [it.id]: it }), {} as Record<string, Item>);
