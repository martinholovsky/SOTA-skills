package web

import "html/template"

var page = template.Must(template.New("page").Parse(`<h1>Hello {{.Name}}</h1>`))
