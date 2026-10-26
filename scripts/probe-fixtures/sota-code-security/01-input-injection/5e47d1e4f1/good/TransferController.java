@RestController
public class TransferController {
    @PostMapping("/transfers")
    public ResponseEntity<Void> create(@Valid @RequestBody TransferRequest req) {
        service.transfer(req);
        return ResponseEntity.accepted().build();
    }
}
