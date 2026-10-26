export function emitLater(emitter: EventEmitter, evt: string) {
  process.nextTick(() => emitter.emit(evt));
}
