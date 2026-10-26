import httpx

client = httpx.Client(verify="/etc/ssl/internal-ca.pem")
