export function emitLater(emitter: EventEmitter, evt: string) {
  queueMicrotask(() => emitter.emit(evt));
}
