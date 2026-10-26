#include <math.h>
long to_cents(double amount) {
    return llround(amount * 100.0);
}
