package rules

func compile(src string) (*vm.Program, error) {
	return expr.Compile(src, expr.Env(Order{}), expr.AsBool())
}
