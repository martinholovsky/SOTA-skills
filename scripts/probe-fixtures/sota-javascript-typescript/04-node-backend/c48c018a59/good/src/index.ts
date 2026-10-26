import { loadSchema } from './schema';
let schemaPromise: ReturnType<typeof loadSchema> | undefined;
export const getSchema = () => (schemaPromise ??= loadSchema());
