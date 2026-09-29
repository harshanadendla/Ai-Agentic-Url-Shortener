package com.example.shortener.service;

import com.example.shortener.domain.ShortLink;
import com.example.shortener.repository.ShortLinkRepository;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.regex.Pattern;

@Service
public class ShortenerService {
    private static final String ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    private static final int GENERATED_CODE_LENGTH = 8;
    private static final int MAX_COLLISION_ATTEMPTS = 8;
    private static final Pattern ALIAS_PATTERN = Pattern.compile("^[A-Za-z0-9_-]{4,32}$");

    private final ShortLinkRepository repository;
    private final UrlPolicy urlPolicy;
    private final LinkCache cache;
    private final SecureRandom random = new SecureRandom();
    private final Counter redirectCounter;

    public ShortenerService(ShortLinkRepository repository, UrlPolicy urlPolicy, LinkCache cache, MeterRegistry meterRegistry) {
        this.repository = repository;
        this.urlPolicy = urlPolicy;
        this.cache = cache;
        this.redirectCounter = Counter.builder("shortener_redirects_total").description("Successful URL redirects").register(meterRegistry);
    }

    @Transactional
    public ShortLink create(String rawUrl, String customAlias, Instant expiresAt) {
        String target = urlPolicy.validateAndNormalize(rawUrl);
        Instant now = Instant.now();
        if (expiresAt != null && !expiresAt.isAfter(now)) throw new IllegalArgumentException("expiresAt must be in the future");

        if (customAlias != null && !customAlias.isBlank()) {
            if (!ALIAS_PATTERN.matcher(customAlias).matches()) throw new IllegalArgumentException("customAlias must be 4-32 URL-safe characters");
            if (repository.existsById(customAlias)) throw new LinkConflictException("custom alias already exists");
            try {
                return persist(customAlias, target, now, expiresAt);
            } catch (DataIntegrityViolationException ex) {
                throw new LinkConflictException("custom alias already exists");
            }
        }

        for (int attempt = 0; attempt < MAX_COLLISION_ATTEMPTS; attempt++) {
            String candidate = randomCode();
            if (repository.existsById(candidate)) continue;
            try { return persist(candidate, target, now, expiresAt); }
            catch (DataIntegrityViolationException ignored) { /* another writer won the race; retry */ }
        }
        throw new IllegalStateException("unable to allocate unique code after bounded retries");
    }

    @Transactional
    public String resolve(String code) {
        LinkCache.CachedLink cached = cache.get(code).orElse(null);
        if (cached != null) {
            int updated = repository.incrementClicks(code, Instant.now());
            if (updated == 0) {
                cache.evict(code);
                throw new LinkNotFoundException("link not found or expired");
            }
            redirectCounter.increment();
            return cached.targetUrl();
        }

        ShortLink link = repository.findById(code).orElseThrow(() -> new LinkNotFoundException("link not found"));
        Instant now = Instant.now();
        if (!link.isActive() || link.isExpired(now)) throw new LinkNotFoundException("link not found or expired");
        repository.incrementClicks(code, now);
        cache.put(code, link.getTargetUrl(), link.getExpiresAt());
        redirectCounter.increment();
        return link.getTargetUrl();
    }

    @Transactional(readOnly = true)
    public ShortLink getActiveOrInactive(String code) {
        return repository.findById(code).orElseThrow(() -> new LinkNotFoundException("link not found"));
    }

    @Transactional
    public void deactivate(String code) {
        ShortLink link = repository.findById(code).orElseThrow(() -> new LinkNotFoundException("link not found"));
        link.deactivate();
        cache.evict(code);
    }

    private ShortLink persist(String code, String target, Instant now, Instant expiresAt) {
        ShortLink saved = repository.saveAndFlush(new ShortLink(code, target, now, expiresAt));
        cache.put(code, target, expiresAt);
        return saved;
    }

    private String randomCode() {
        StringBuilder b = new StringBuilder(GENERATED_CODE_LENGTH);
        for (int i = 0; i < GENERATED_CODE_LENGTH; i++) b.append(ALPHABET.charAt(random.nextInt(ALPHABET.length())));
        return b.toString();
    }
}
