if (req.headers.origin.startsWith("https://app.example.com")) {
  res.set("Access-Control-Allow-Origin", req.headers.origin);
}
