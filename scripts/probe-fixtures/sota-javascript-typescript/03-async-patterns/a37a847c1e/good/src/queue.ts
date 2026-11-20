queue = queue.then(() => task()).catch((e) => logger.error(e));
