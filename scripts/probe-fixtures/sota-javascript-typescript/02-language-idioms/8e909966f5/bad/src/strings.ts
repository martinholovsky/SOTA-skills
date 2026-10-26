export class StringUtils {
  static capitalize(s: string) {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
}
