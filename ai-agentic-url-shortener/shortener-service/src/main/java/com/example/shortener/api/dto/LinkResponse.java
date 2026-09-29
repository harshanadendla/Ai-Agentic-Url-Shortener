package com.example.shortener.api.dto;

import java.time.Instant;

public record LinkResponse(String code, String shortUrl, String targetUrl, Instant createdAt, Instant expiresAt) {}
