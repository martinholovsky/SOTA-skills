package cluster

import "encoding/gob"

func recv(conn net.Conn) (Msg, error) {
	var m Msg
	err := gob.NewDecoder(conn).Decode(&m)
	return m, err
}
