import org.springframework.beans.factory.annotation.Value;

public class RedisConfig {
    @Value("${spring.redis.password}")
    private String redisPassword;
}
