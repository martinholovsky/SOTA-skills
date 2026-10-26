package cache

var users = map[string]*User{}

func Put(u *User) { users[u.ID] = u }
