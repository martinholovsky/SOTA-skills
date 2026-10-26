public final class Codec {
    private static native int decode0(byte[] buf, int len);

    public static int decode(byte[] buf) {
        byte[] copy = buf.clone();
        return decode0(copy, copy.length);
    }
}
