package com.example.shortener.api.dto;

import java.time.Instant;

public record AnalyticsResponse(String code, long clicks, boolean active, Instant createdAt, Instant expiresAt, Instant lastAccessedAt) {}
