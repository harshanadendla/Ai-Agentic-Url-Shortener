package com.example.shortener.api.dto;

import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.Instant;

public record CreateLinkRequest(
        @Size(max = 2048) String url,
        @Pattern(regexp = "^[A-Za-z0-9_-]{4,32}$", message = "customAlias must be 4-32 URL-safe characters") String customAlias,
        @Future Instant expiresAt) {
}
