import Ajv from 'ajv';
const ajv = new Ajv({ strict: true });
export const validateBody = ajv.compile(bodySchema);
