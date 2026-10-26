SELECT id, name
FROM stores
WHERE ST_DWithin(location, ST_MakePoint($1, $2)::geography, 5000)
ORDER BY location <-> ST_MakePoint($1, $2)::geography
LIMIT 20;
