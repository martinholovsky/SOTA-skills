package rules

func compile(src string) (*vm.Program, error) {
	return expr.Compile(src)
}
