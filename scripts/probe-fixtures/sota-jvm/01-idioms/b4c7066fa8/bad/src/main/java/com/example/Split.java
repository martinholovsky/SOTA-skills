package com.example;

import java.math.BigDecimal;

final class Split {
    static BigDecimal share(BigDecimal total, BigDecimal parts) {
        return total.divide(parts);
    }
}
