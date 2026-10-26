package com.example;

import java.math.BigDecimal;
import java.math.RoundingMode;

final class Split {
    static BigDecimal share(BigDecimal total, BigDecimal parts) {
        return total.divide(parts, 2, RoundingMode.HALF_EVEN);
    }
}
