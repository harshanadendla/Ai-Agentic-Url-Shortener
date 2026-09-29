package com.example.shortener.api;

import com.example.shortener.domain.ShortLink;
import com.example.shortener.service.ShortenerService;
import com.example.shortener.reliability.CreateRateLimitFilter;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(controllers = LinkController.class)
@AutoConfigureMockMvc(addFilters = false)
class LinkControllerTest {
    @Autowired MockMvc mvc;
    @MockBean ShortenerService service;
    @MockBean CreateRateLimitFilter rateLimitFilter;

    @Test
    void createsLink() throws Exception {
        when(service.create(any(), any(), any())).thenReturn(new ShortLink("abc12345", "https://example.com", Instant.parse("2026-09-24T18:00:00Z"), null));
        mvc.perform(post("/api/v1/links").contentType("application/json").content("{\"url\":\"https://example.com\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value("abc12345"));
    }
}
