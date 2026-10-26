plugins {
    kotlin("jvm") version "2.2.0"
}

kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xconsistent-data-class-copy-visibility")
    }
}
