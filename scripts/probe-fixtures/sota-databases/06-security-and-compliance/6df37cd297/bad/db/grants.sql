CREATE LOGIN app_login WITH PASSWORD = '$(APP_PW)';
CREATE USER app_login FOR LOGIN app_login;
EXEC sp_addrolemember 'db_owner', 'app_login';
