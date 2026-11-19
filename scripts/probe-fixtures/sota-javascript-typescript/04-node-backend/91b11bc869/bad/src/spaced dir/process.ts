process.on('uncaughtException', (err) => {
  logger.error({ err }, 'ignored, carrying on');
});
