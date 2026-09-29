package com.example.shortener.reliability;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;

@Component
public class CreateRateLimitFilter extends OncePerRequestFilter {
    private final StringRedisTemplate redis;
    private final int perMinute;
    private final Counter failOpen;

    public CreateRateLimitFilter(StringRedisTemplate redis, MeterRegistry registry,
                                 @Value("${shortener.create-rate-limit-per-minute:60}") int perMinute) {
        this.redis = redis;
        this.perMinute = perMinute;
        this.failOpen = Counter.builder("shortener_rate_limit_fail_open_total").description("Redis failures where traffic was allowed").register(registry);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !("POST".equalsIgnoreCase(request.getMethod()) && "/api/v1/links".equals(request.getRequestURI()));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        try {
            long minute = Instant.now().getEpochSecond() / 60;
            String key = "create-rate:" + request.getRemoteAddr() + ":" + minute;
            Long count = redis.opsForValue().increment(key);
            if (count != null && count == 1L) redis.expire(key, Duration.ofSeconds(70));
            if (count != null && count > perMinute) {
                response.setStatus(429);
                response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
                response.getWriter().write("{\"title\":\"Rate limit exceeded\",\"status\":429}");
                return;
            }
        } catch (RuntimeException ex) {
            failOpen.increment(); // availability-first: DB/API still function during Redis outage
        }
        chain.doFilter(request, response);
    }
}
