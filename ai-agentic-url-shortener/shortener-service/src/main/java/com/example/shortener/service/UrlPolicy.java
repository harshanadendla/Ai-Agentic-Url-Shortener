package com.example.shortener.service;

import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;
import java.util.Set;

@Component
public class UrlPolicy {
    private static final Set<String> ALLOWED_SCHEMES = Set.of("http", "https");

    public String validateAndNormalize(String raw) {
        if (raw == null || raw.isBlank() || raw.length() > 2048) {
            throw new IllegalArgumentException("url is required and must be at most 2048 characters");
        }
        if (raw.chars().anyMatch(Character::isISOControl)) {
            throw new IllegalArgumentException("url contains control characters");
        }
        try {
            URI uri = new URI(raw.trim()).normalize();
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
            if (!ALLOWED_SCHEMES.contains(scheme) || uri.getHost() == null || uri.getHost().isBlank()) {
                throw new IllegalArgumentException("url must be an absolute http/https URL");
            }
            return uri.toString();
        } catch (URISyntaxException ex) {
            throw new IllegalArgumentException("url is malformed", ex);
        }
    }
}
