CREATE LOGIN app_login WITH PASSWORD = '$(APP_PW)';
CREATE USER app_login FOR LOGIN app_login;
ALTER ROLE api_executor ADD MEMBER app_login;
GRANT EXECUTE ON SCHEMA::api TO api_executor;
