package com.example;

import edu.umd.cs.findbugs.annotations.SuppressFBWarnings;

final class Snapshot {

    private final java.util.List<String> names;
    Snapshot(java.util.List<String> names) { this.names = java.util.List.copyOf(names); }

    @SuppressFBWarnings("EI_EXPOSE_REP")
    java.util.List<String> names() { return names; }
}
