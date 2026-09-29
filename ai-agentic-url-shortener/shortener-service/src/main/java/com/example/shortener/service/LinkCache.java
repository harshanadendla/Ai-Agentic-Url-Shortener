package com.example.shortener.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

@Component
public class LinkCache {
    private final StringRedisTemplate redis;
    private final ObjectMapper mapper;
    private final Duration defaultTtl;
    private final Counter failures;

    public LinkCache(StringRedisTemplate redis, ObjectMapper mapper, MeterRegistry meterRegistry,
                     @Value("${shortener.cache-ttl:PT24H}") Duration defaultTtl) {
        this.redis = redis;
        this.mapper = mapper;
        this.defaultTtl = defaultTtl;
        this.failures = Counter.builder("shortener_cache_failures_total").description("Redis cache failures; DB fallback is used").register(meterRegistry);
    }

    public Optional<CachedLink> get(String code) {
        try {
            String value = redis.opsForValue().get(key(code));
            if (value == null) return Optional.empty();
            CachedLink cached = mapper.readValue(value, CachedLink.class);
            if (cached.expiresAt() != null && !cached.expiresAt().isAfter(Instant.now())) {
                evict(code);
                return Optional.empty();
            }
            return Optional.of(cached);
        } catch (Exception ex) {
            failures.increment();
            return Optional.empty(); // reliability choice: cache outage must not break redirects
        }
    }

    public void put(String code, String targetUrl, Instant expiresAt) {
        try {
            Duration ttl = defaultTtl;
            if (expiresAt != null) {
                ttl = Duration.between(Instant.now(), expiresAt);
                if (ttl.isNegative() || ttl.isZero()) return;
                if (ttl.compareTo(defaultTtl) > 0) ttl = defaultTtl;
            }
            redis.opsForValue().set(key(code), mapper.writeValueAsString(new CachedLink(targetUrl, expiresAt)), ttl);
        } catch (JsonProcessingException | RuntimeException ex) {
            failures.increment(); // fail open to DB
        }
    }

    public void evict(String code) {
        try { redis.delete(key(code)); } catch (RuntimeException ex) { failures.increment(); }
    }

    private String key(String code) { return "short-link:" + code; }

    public record CachedLink(String targetUrl, Instant expiresAt) {}
}
