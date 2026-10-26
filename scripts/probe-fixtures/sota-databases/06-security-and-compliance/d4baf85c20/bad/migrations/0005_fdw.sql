CREATE SERVER reporting FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host 'reports', dbname 'rpt');
CREATE USER MAPPING FOR PUBLIC SERVER reporting OPTIONS (user 'rpt_reader', password 'x');
