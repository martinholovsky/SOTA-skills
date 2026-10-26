fun sync() {
    try { api.pull() } catch (e: IOException) { log.warn("sync failed: %s", e.javaClass.simpleName) }
}
