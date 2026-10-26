plugins {
    java
}

tasks.test {
    useJUnitPlatform()
    jvmArgs("-Xcheck:jni")
}
