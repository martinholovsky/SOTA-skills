fun sync() {
    try { api.pull() } catch (e: IOException) { e.printStackTrace() }
}
