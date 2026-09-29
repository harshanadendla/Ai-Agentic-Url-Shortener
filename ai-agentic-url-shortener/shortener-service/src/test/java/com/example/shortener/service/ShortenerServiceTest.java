package com.example.shortener.service;

import com.example.shortener.domain.ShortLink;
import com.example.shortener.repository.ShortLinkRepository;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ShortenerServiceTest {
    private final ShortLinkRepository repository = mock(ShortLinkRepository.class);
    private final LinkCache cache = mock(LinkCache.class);
    private final ShortenerService service = new ShortenerService(repository, new UrlPolicy(), cache, new SimpleMeterRegistry());

    @Test
    void createsCustomAlias() {
        when(repository.existsById("docs1")).thenReturn(false);
        when(repository.saveAndFlush(any())).thenAnswer(inv -> inv.getArgument(0));
        ShortLink result = service.create("https://example.com/docs", "docs1", Instant.now().plusSeconds(3600));
        assertThat(result.getCode()).isEqualTo("docs1");
        verify(cache).put(any(), any(), any());
    }

    @Test
    void rejectsAliasConflict() {
        when(repository.existsById("docs1")).thenReturn(true);
        assertThatThrownBy(() -> service.create("https://example.com", "docs1", null)).isInstanceOf(LinkConflictException.class);
    }

    @Test
    void resolvesFromDatabaseAndIncrementsAnalytics() {
        ShortLink link = new ShortLink("abc12345", "https://example.com", Instant.now(), null);
        when(cache.get("abc12345")).thenReturn(Optional.empty());
        when(repository.findById("abc12345")).thenReturn(Optional.of(link));
        assertThat(service.resolve("abc12345")).isEqualTo("https://example.com");
        verify(repository).incrementClicks(any(), any());
        verify(cache).put(any(), any(), any());
    }
}
