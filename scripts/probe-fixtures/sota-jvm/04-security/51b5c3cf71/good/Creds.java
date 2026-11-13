import lombok.Data;
import lombok.ToString;

@Data
public class Creds {
    private String user;
    @ToString.Exclude
    private char[] password;
}
