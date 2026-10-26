import Ajv from 'ajv';
const ajv = new Ajv({ allErrors: true });
export const validateBody = ajv.compile(bodySchema);
