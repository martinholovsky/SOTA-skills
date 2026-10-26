public class OrderRequest {
    @Valid
    @NotNull
    private AddressDto shippingAddress;
    @Valid
    private List<LineItemDto> items;
    private @Valid PaymentDto payment;
}
