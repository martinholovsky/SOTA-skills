package com.example;

import com.alibaba.fastjson.parser.ParserConfig;

final class Json {

    static { ParserConfig.getGlobalInstance().setAutoTypeSupport(true); }
}
