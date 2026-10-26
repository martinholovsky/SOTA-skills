SELECT id, name
FROM stores
WHERE ST_Distance(location, ST_MakePoint($1, $2)::geography) < 5000;
