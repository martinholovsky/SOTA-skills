package com.example;

import org.springframework.expression.spel.standard.SpelExpressionParser;

final class Rules {

    static Object eval(String expr) {
        return new SpelExpressionParser().parseExpression(expr).getValue();
    }
}
