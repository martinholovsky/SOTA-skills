package cluster

import "encoding/json"

func recv(conn net.Conn) (Msg, error) {
	var m Msg
	dec := json.NewDecoder(io.LimitReader(conn, 1<<20))
	dec.DisallowUnknownFields()
	err := dec.Decode(&m)
	return m, err
}
