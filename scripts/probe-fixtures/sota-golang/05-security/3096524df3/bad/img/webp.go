package img

// #cgo LDFLAGS: -lwebp
// #include <webp/decode.h>
import "C"

func Version() int { return int(C.WebPGetDecoderVersion()) }
