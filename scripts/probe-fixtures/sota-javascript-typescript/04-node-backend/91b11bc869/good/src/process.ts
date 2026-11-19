process.on('uncaughtException', (err) => {
  logger.fatal({ err }, 'uncaught exception — exiting');
  // flush logs/telemetry synchronously if needed, then:
  process.exit(1);
});
