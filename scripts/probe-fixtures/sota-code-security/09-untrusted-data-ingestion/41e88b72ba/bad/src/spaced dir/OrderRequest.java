public class OrderRequest {
    @NotNull
    private AddressDto shippingAddress;
    private List<LineItemDto> items;
}
