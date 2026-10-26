package cache

type Cache struct {
	mu    sync.Mutex
	users map[string]*User
}

func New() *Cache { return &Cache{users: map[string]*User{}} }
