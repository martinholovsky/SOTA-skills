export const byId = (items: Item[]) =>
  items.reduce((acc, it) => { acc.set(it.id, it); return acc; }, new Map<string, Item>());
