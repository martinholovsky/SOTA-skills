export function ResultCount({ count }: { count: number }) {
  return <p>{t('search.resultCount', { count })}</p>;
}
