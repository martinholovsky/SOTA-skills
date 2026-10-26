class App : Application() {
    override fun onCreate() {
        super.onCreate()
        if (Debug.isDebuggerConnected()) integrity.report("debugger")
        initPayments()
    }
}
