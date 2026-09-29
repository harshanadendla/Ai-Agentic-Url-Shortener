package com.example.shortener.repository;

import com.example.shortener.domain.ShortLink;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;

public interface ShortLinkRepository extends JpaRepository<ShortLink, String> {
    @Modifying(clearAutomatically = true, flushAutomatically = true)
    @Query("update ShortLink s set s.clickCount = s.clickCount + 1, s.lastAccessedAt = :accessedAt where s.code = :code and s.active = true and (s.expiresAt is null or s.expiresAt > :accessedAt)")
    int incrementClicks(@Param("code") String code, @Param("accessedAt") Instant accessedAt);
}
