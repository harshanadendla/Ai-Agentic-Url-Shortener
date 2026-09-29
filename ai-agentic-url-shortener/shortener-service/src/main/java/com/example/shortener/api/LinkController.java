package com.example.shortener.api;

import com.example.shortener.api.dto.AnalyticsResponse;
import com.example.shortener.api.dto.CreateLinkRequest;
import com.example.shortener.api.dto.LinkResponse;
import com.example.shortener.domain.ShortLink;
import com.example.shortener.service.ShortenerService;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
@RequestMapping("/api/v1/links")
public class LinkController {
    private final ShortenerService service;
    private final String publicBaseUrl;

    public LinkController(ShortenerService service, @Value("${shortener.public-base-url:http://localhost:8080}") String publicBaseUrl) {
        this.service = service;
        this.publicBaseUrl = publicBaseUrl.replaceAll("/$", "");
    }

    @PostMapping
    public ResponseEntity<LinkResponse> create(@Valid @RequestBody CreateLinkRequest request) {
        ShortLink link = service.create(request.url(), request.customAlias(), request.expiresAt());
        LinkResponse body = new LinkResponse(link.getCode(), publicBaseUrl + "/" + link.getCode(), link.getTargetUrl(), link.getCreatedAt(), link.getExpiresAt());
        return ResponseEntity.created(URI.create(body.shortUrl())).body(body);
    }

    @GetMapping("/{code}/analytics")
    public AnalyticsResponse analytics(@PathVariable String code) {
        ShortLink link = service.getActiveOrInactive(code);
        return new AnalyticsResponse(link.getCode(), link.getClickCount(), link.isActive(), link.getCreatedAt(), link.getExpiresAt(), link.getLastAccessedAt());
    }

    @DeleteMapping("/{code}")
    public ResponseEntity<Void> deactivate(@PathVariable String code) {
        service.deactivate(code);
        return ResponseEntity.noContent().build();
    }
}
