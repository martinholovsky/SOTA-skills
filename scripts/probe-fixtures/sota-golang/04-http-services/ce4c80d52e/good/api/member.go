package api

import json "encoding/json/v2"

type UpdateMember struct {
	Name string `json:"name"`
	Role string `json:"role"`
}

func decode(r *http.Request) (UpdateMember, error) {
	var in UpdateMember
	err := json.UnmarshalRead(r.Body, &in)
	return in, err
}
