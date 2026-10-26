package com.example;

import javax.sql.DataSource;

final class Lookup {

    private final DataSource dataSource;

    Lookup(DataSource dataSource) { this.dataSource = dataSource; }
}
