package clock

import "math/rand/v2"

var r = rand.New(rand.NewPCG(1, 2)) // deterministic jitter, test only
