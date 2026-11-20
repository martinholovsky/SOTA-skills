package web

var policy = bluemonday.UGCPolicy()

func Body(src []byte) template.HTML {
	return template.HTML(policy.SanitizeBytes(markdown.ToHTML(src, nil, nil)))
}
