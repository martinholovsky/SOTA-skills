package com.example;

public final class Creds {
    private final String user;
    private final char[] password;

    public Creds(String user, char[] password) {
        this.user = user;
        this.password = password.clone();
    }

    @Override
    public String toString() {
        return "Creds[user=" + user + ", password=***]";
    }
}
