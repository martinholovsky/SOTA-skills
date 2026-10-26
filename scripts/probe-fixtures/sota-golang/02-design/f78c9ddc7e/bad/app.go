package app

var db *sql.DB

func init() { db = mustOpen(os.Getenv("DSN")) }
