package web

func Body(src []byte) template.HTML {
	return template.HTML(markdown.ToHTML(src, nil, nil))
}
