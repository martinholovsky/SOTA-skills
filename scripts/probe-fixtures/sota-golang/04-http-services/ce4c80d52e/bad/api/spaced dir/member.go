package api

import "encoding/json"

type UpdateMember struct {
	Name string `json:"name"`
	Role string `json:"role"`
}

func decode(r *http.Request) (UpdateMember, error) {
	var in UpdateMember
	err := json.NewDecoder(r.Body).Decode(&in)
	return in, err
}
